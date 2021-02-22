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

import os
import time

from .const import DOMAIN, _LOGGER
from .plex_assistant import PlexAssistant
from .process_speech import ProcessSpeech
from .localize import translations
from .helpers import (
    filter_media,
    find_media,
    fuzzy,
    get_devices,
    get_server,
    listeners,
    media_error,
    media_service,
    no_device_error,
    play_tts_error,
    process_config_item,
    remote_control,
    run_start_script,
    seek_to_offset,
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
    start_script = process_config_item(entry.options, "start_script")
    keyword_replace = process_config_item(entry.options, "keyword_replace")
    jump_amount = [entry.options.get("jump_f") or 30, entry.options.get("jump_b") or 15]
    zeroconf = await async_get_instance(hass)

    server = await get_server(hass, hass.config, server_name)
    if not server:
        return True

    def pa_executor(_server, start_script_keys):
        _pa = PlexAssistant(_server, start_script_keys)
        get_devices(hass, _pa)
        return _pa

    pa = await hass.async_add_executor_job(pa_executor, server, list(start_script.keys()))

    ifttt_listener = await listeners(hass)
    hass.data[DOMAIN][entry.entry_id] = {"remove_listener": ifttt_listener}

    tts_dir = hass.config.path() + "/www/plex_assist_tts/"
    if tts_errors and not os.path.exists(tts_dir):
        os.makedirs(tts_dir, mode=0o777)

    entry.add_update_listener(async_reload_entry)

    def handle_input(call):
        hass.services.async_call("plex", "scan_for_clients", blocking=False, limit=30)
        command = call.data.get("command").strip()
        media = None

        if not command:
            _LOGGER.warning(localize["no_call"])
            return
        _LOGGER.debug("Command: %s", command)

        command = command.lower()
        if keyword_replace and any(keyword.lower() in command for keyword in keyword_replace.keys()):
            for keyword in keyword_replace.keys():
                command = command.replace(keyword.lower(), keyword_replace[keyword].lower())

        get_devices(hass, pa)
        command = ProcessSpeech(pa, localize, command, default_device).results
        _LOGGER.debug("Processed Command: %s", {i: command[i] for i in command if i != "library" and command[i]})

        if not command["device"] and not default_device:
            no_device_error(localize)
            return

        if pa.media["updated"] < pa.library.search(sort="addedAt:desc", limit=1)[0].addedAt:
            pa.update_libraries()

        device = fuzzy(command["device"] or default_device, pa.device_names)
        device = run_start_script(hass, pa, command, start_script, device)

        _LOGGER.debug("PA Devices: %s", pa.devices)
        if device[1] < 60:
            no_device_error(localize, command["device"])
            return
        _LOGGER.debug("Device: %s", device[0])

        device = pa.devices[device[0]]

        if command["control"]:
            remote_control(hass, zeroconf, command["control"], device)
            return

        try:
            media, library = find_media(command, command["media"], pa.media)
            media = filter_media(pa, command, media, library)
        except:
            error = media_error(command, localize)
            if tts_errors:
                play_tts_error(hass, tts_dir, device["entity_id"], error, lang)
        _LOGGER.debug("Media: %s", str(media))

        shuffle = 1 if command["random"] else 0
        offset = (media.viewOffset / 1000) - 5 if getattr(media, "viewOffset", 0) > 15 and not command["random"] else 0

        if getattr(media, "TYPE", None) == "episode":
            episodes = media.show().episodes()
            episodes = episodes[episodes.index(media):]
            media = pa.server.createPlayQueue(episodes, shuffle=shuffle)
        elif getattr(media, "TYPE", None) in ["artist", "album"]:
            tracks = media.tracks()
            media = pa.server.createPlayQueue(tracks, shuffle=shuffle)
        elif getattr(media, "TYPE", None) == "track":
            tracks = media.album().tracks()
            tracks = tracks[tracks.index(media):]
            media = pa.server.createPlayQueue(tracks, shuffle=shuffle)
        elif not getattr(media, "TYPE", None) == "playqueue":
            media = pa.server.createPlayQueue(media, shuffle=shuffle)

        payload = '%s{"playqueue_id": %s, "type": "%s"}' % (
            "plex://" if device["device_type"] in ["cast", "sonos"] else "",
            media.playQueueID,
            media.playQueueType
        )

        media_service(hass, device["entity_id"], "play_media", payload)
        seek_to_offset(hass, offset, device["entity_id"])

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
