"""
Plex Assistant is a component for Home Assistant to add control of Plex to
Google Assistant with a little help from IFTTT or DialogFlow.

Play to Google Cast devices or Plex Clients using fuzzy searches for media and
cast device names.

https://github.com/maykar/plex_assistant
"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant
from homeassistant.components.plex.services import get_plex_server
from homeassistant.components.zeroconf import async_get_instance
from pychromecast.controllers.plex import PlexController
from datetime import timedelta

import os
import json
import time

from .const import DOMAIN, _LOGGER
from .plex_assistant import PlexAssistant
from .process_speech import ProcessSpeech
from .localize import translations
from .helpers import (
    cast_next_prev,
    device_responding,
    filter_media,
    find_media,
    fuzzy,
    get_devices,
    get_server,
    jump,
    listeners,
    media_error,
    media_service,
    no_device_error,
    play_tts_error,
)


async def async_setup(hass: HomeAssistant, config: Config):
    if DOMAIN in config:
        changes_url = "https://github.com/maykar/plex_assistant/blob/master/ver_one_update.md"
        message = "Configuration is now handled in the UI, please read the %s for how to migrate to the new version and more info.%s"
        service_data = {
            "title": "Plex Assistant Breaking Changes",
            "message": message % (f"[change log]({changes_url})", "."),
        }
        await hass.services.async_call("persistent_notification", "create", service_data, False)
        _LOGGER.warning("Plex Assistant: " + message % ("change log", f". {changes_url}"))
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    server_name = entry.data.get("server_name")
    default_device = entry.data.get("default_cast")
    tts_errors = entry.data.get("tts_errors")
    lang = entry.data.get("language")
    localize = translations[lang]
    start_script = entry.options.get("start_script")
    keyword_replace = entry.options.get("keyword_replace")
    jump_amount = [entry.options.get("jump_f") or 30, entry.options.get("jump_b") or 15]
    zeroconf = await async_get_instance(hass)
    plex_c = PlexController()

    if start_script:
        try:
            start_script = json.loads("{" + start_script + "}")
            if start_script:
                for script in start_script.keys():
                    _LOGGER.debug(f"Script {script}: {start_script[script]}")
        except:
            start_script = None
            _LOGGER.warning("Plex Assistant: There is a formatting issue with your client start script config.")
    start_script_keys = list(start_script.keys()) if start_script else []

    if keyword_replace:
        try:
            keyword_replace = json.loads("{" + keyword_replace + "}")
            for word in keyword_replace.keys():
                _LOGGER.debug(f"Replace '{word}' with '{keyword_replace[word]}'")
        except:
            keyword_replace = None
            _LOGGER.warning("Plex Assistant: There is a formatting issue with your keyword replacement config.")

    server = await get_server(hass, hass.config, server_name)
    if not server:
        return True

    def pa_executor(_server, start_script_keys):
        _pa = PlexAssistant(_server, start_script_keys)
        get_devices(hass, _pa)
        return _pa

    pa = await hass.async_add_executor_job(pa_executor, server, start_script_keys)

    ifttt_listener = await listeners(hass)
    hass.data[DOMAIN][entry.entry_id] = {"remove_listener": ifttt_listener}

    tts_dir = hass.config.path() + "/www/plex_assist_tts/"
    if tts_errors and not os.path.exists(tts_dir):
        os.makedirs(tts_dir, mode=0o777)

    entry.add_update_listener(async_reload_entry)

    def handle_input(call):
        offset = None
        media = None

        command = call.data.get("command").strip()
        _LOGGER.debug("Command: %s", command)

        if not command:
            _LOGGER.warning(localize["no_call"])
            return

        command = command.lower()

        if keyword_replace and any(keyword.lower() in command for keyword in keyword_replace.keys()):
            for keyword in keyword_replace.keys():
                command = command.replace(keyword.lower(), keyword_replace[keyword].lower())

        get_devices(hass, pa)

        command = ProcessSpeech(pa, localize, command, default_device)
        command = command.results

        command_debug = {i: command[i] for i in command if i != "library" and command[i]}
        command_debug = str(command_debug).replace("'", "").replace(":", " =")
        _LOGGER.debug(f"Processed Command: {command_debug[1:-1]}")

        if not command["device"] and not default_device:
            no_device_error(localize)
            return

        if pa.media["updated"] < pa.library.search(sort="addedAt:desc", limit=1)[0].addedAt:
            pa.update_libraries()

        device = fuzzy(command["device"] or default_device, pa.device_names)

        responding = True
        if device[0] in start_script_keys:
            timeout = 0
            started = False
            responding = False
            woken = False
            start_time = time.time()
            while timeout < 30 and device[0] not in pa.devices:
                started = True
                if timeout == 0:
                    hass.services.call("script", start_script[device[0]].replace("script.", ""))
                    time.sleep(5)
                    hass.services.call("plex", "scan_for_clients")
                else:
                    time.sleep(1)
                if (timeout % 2) == 0 or timeout == 0:
                    get_devices(hass, pa)
                timeout += 1

            if started:
                hass.services.async_call("plex", "scan_for_clients")
                get_devices(hass, pa)

            if device[0] in pa.devices:
                stop = False
                while not responding and not stop:
                    if not started:
                        hass.services.call("script", start_script[device[0]].replace("script.", ""))
                    responding = device_responding(hass, pa, device[0])
                    stop = True
            total_time = timedelta(seconds=time.time()) - timedelta(seconds=start_time)

            if responding and not started and total_time > timedelta(seconds=1):
                time.sleep(5)

            device = fuzzy(command["device"] or default_device, list(pa.devices.keys()))

        _LOGGER.debug("PA Devices: %s", pa.devices)

        if device[1] < 60 or not responding:
            no_device_error(localize, command["device"])
            return
        else:
            _LOGGER.debug("Device: %s", device[0])
            device = pa.devices[device[0]]

        if command["control"] == "jump_forward":
            jump(hass, device, jump_amount[0])
            return
        elif command["control"] == "jump_back":
            jump(hass, device, -jump_amount[1])
            return
        elif command["control"] == "next_track" and device["device_type"] == "cast":
            cast_next_prev(hass, zeroconf, plex_c, device, "next")
            return
        elif command["control"] == "previous_track" and device["device_type"] == "cast":
            cast_next_prev(hass, zeroconf, plex_c, device, "previous")
            return
        elif command["control"]:
            media_service(hass, device["entity_id"], f"media_{command['control']}")
            return

        try:
            result = find_media(command, command["media"], pa.media)
            media = filter_media(pa, command, result["media"], result["library"])
        except:
            error = media_error(command, localize)
            if tts_errors:
                play_tts_error(hass, tts_dir, device["entity_id"], error, lang)

        _LOGGER.debug("Media: %s", str(media))

        if getattr(media, "viewOffset", 0) > 10 and not command["random"]:
            offset = (media.viewOffset / 1000) - 5

        shuffle = 1 if command["random"] else 0

        if getattr(media, "TYPE", None) == "episode":
            episodes = media.show().episodes()
            episodes = episodes[episodes.index(media):]
            media = pa.server.createPlayQueue(episodes, shuffle=shuffle)

        if not getattr(media, "TYPE", None) == "playqueue":
            media = pa.server.createPlayQueue(media, shuffle=shuffle)

        payload = '{"playqueue_id": %s, "type": "%s"}' % (
            media.playQueueID,
            media.playQueueType,
        )

        if device["device_type"] in ["cast", "sonos"]:
            payload = "plex://" + payload

        media_service(hass, device["entity_id"], "play_media", payload)

        if offset:
            timeout = 0
            while not hass.states.is_state(device["entity_id"], "playing") and timeout < 200:
                time.sleep(0.25)
                timeout += 1

            if device["device_type"] in ["cast", "sonos"]:
                timeout = 0
                while hass.states.get(device["entity_id"]).attributes.get("media_position", 0) == 0 and timeout < 200:
                    time.sleep(0.25)
                    timeout += 1
            else:
                time.sleep(0.75)

            if hass.states.is_state(device["entity_id"], "playing"):
                media_service(hass, device["entity_id"], "media_seek", offset)

    hass.services.async_register(DOMAIN, "command", handle_input)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.services.async_remove(DOMAIN, "command")
    hass.data[DOMAIN][entry.entry_id]["remove_listener"]()
    hass.data[DOMAIN].pop(entry.entry_id)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
