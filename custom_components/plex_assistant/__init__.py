"""
Plex Assistant is a component for Home Assistant to add control of Plex to
Google Assistant with a little help from IFTTT or DialogFlow.

Play to Google Cast devices or Plex Clients using fuzzy searches for media and
cast device names.

https://github.com/maykar/plex_assistant
"""

import logging
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

DOMAIN = "plex_assistant"
CONF_URL = "url"
CONF_TOKEN = "token"
CONF_SERVER_NAME = "server_name"
CONF_DEFAULT_CAST = "default_cast"
CONF_LANG = "language"
CONF_TTS_ERROR = "tts_errors"
REMOTE_SERVER = "remote_server"
CONF_ALIASES = "aliases"
CONF_START_SCRIPT = "start_script"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: {
            vol.Optional(CONF_URL): cv.url,
            vol.Optional(CONF_TOKEN): cv.string,
            vol.Optional(CONF_SERVER_NAME): cv.string,
            vol.Optional(CONF_DEFAULT_CAST): cv.string,
            vol.Optional(CONF_LANG, default="en"): cv.string,
            vol.Optional(CONF_TTS_ERROR, default=True): cv.boolean,
            vol.Optional(REMOTE_SERVER, default=False): cv.boolean,
            vol.Optional(CONF_ALIASES, default={}): vol.Any(dict),
            vol.Optional(CONF_START_SCRIPT, default={}): vol.Any(dict),
        }
    },
    extra=vol.ALLOW_EXTRA,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Called when Home Assistant is loading our component."""

    import os
    import time

    from gtts import gTTS
    from homeassistant.helpers.network import get_url
    from homeassistant.components.zeroconf import async_get_instance
    from pychromecast.controllers.plex import PlexController
    from homeassistant.components.plex.services import get_plex_server
    from plexapi.server import PlexServer

    from .plex_assistant import PlexAssistant
    from .localize import LOCALIZE
    from .helpers import (
        find_media,
        fuzzy,
        media_error,
        filter_media,
        process_speech,
        update_sensor,
    )

    conf = config[DOMAIN]
    url = conf.get(CONF_URL)
    token = conf.get(CONF_TOKEN)
    server_name = conf.get(CONF_SERVER_NAME)
    default_device = conf.get(CONF_DEFAULT_CAST)
    lang = conf.get(CONF_LANG)
    tts_errors = conf.get(CONF_TTS_ERROR)
    remote_server = conf.get(REMOTE_SERVER)
    aliases = conf.get(CONF_ALIASES)
    start_script = conf.get(CONF_START_SCRIPT)
    zconf = await async_get_instance(hass)
    localize = LOCALIZE[lang] if lang in LOCALIZE.keys() else LOCALIZE["en"]
    server = None

    # Find or create the directory to hold TTS error MP3s.
    dir = hass.config.path() + "/www/plex_assist_tts/"
    if tts_errors and not os.path.exists(dir):
        os.makedirs(dir, mode=0o777)

    if url and token:
        server = PlexServer(url, token)
    else:
        await hass.helpers.discovery.async_discover(None, None, "plex", config)
        server = get_plex_server(hass, server_name or None)._plex_server

    if not server:
        _LOGGER.warning("Plex Assistant: Plex server not found.")
        return False

    def pa_executor(zconf, url, token, aliases, remote_server, server):
        PA = PlexAssistant(zconf, token, aliases, remote_server, server)
        time.sleep(5)
        update_sensor(hass, PA)
        return PA

    PA = await hass.async_add_executor_job(
        pa_executor, zconf, url, token, aliases, remote_server, server
    )

    def handle_input(call):
        offset = 0
        player = None
        alias = ["", 0]
        media = None
        result = None

        # Update devices at start of call in case new ones have appeared.
        PA.update_devices()

        if not call.data.get("command").strip():
            _LOGGER.warning(localize["no_call"])
            return
        command = call.data.get("command").strip().lower()
        _LOGGER.debug("Command: %s", command)

        update_sensor(hass, PA)
        if localize["controls"]["update_sensor"] in command:
            return

        # Return a dict of the options processed from the speech command.
        command = process_speech(command, localize, default_device, PA)

        if not command["control"]:
            _LOGGER.debug({i: command[i] for i in command if i != "library"})

        # Update libraries if the latest item was added after last lib update.
        if PA.lib["updated"] < PA.plex.search(sort="addedAt:desc", limit=1)[0].addedAt:
            PA.update_libraries()

        if not command["device"] and not default_device:
            _LOGGER.warning(
                "{0} {1}.".format(
                    localize["cast_device"].capitalize(),
                    localize["not_found"],
                )
            )
            return

        # Get the closest name match to device in command, fuzzy returns its name and score.
        devices = PA.chromecast_names + PA.plex_client_names + PA.plex_client_ids
        device = fuzzy(command["device"] or default_device, devices)
        if aliases:
            alias = fuzzy(command["device"] or default_device, PA.alias_names)

        # Call start_script if set for device and device not found
        if (
            (aliases and aliases[alias[0]] not in devices)
            or (alias[1] < 60 and device[1] < 60)
        ) and start_script:
            pre_device = command["device"] or default_device
            if pre_device in start_script:
                attempts = 0
                while (
                    (aliases and aliases[alias[0]] not in devices)
                    or (alias[1] < 60 and device[1] < 60)
                ) and attempts < (start_script[pre_device]["attempts"] or 2):
                    hass.services.call(
                        "script",
                        start_script[pre_device]["script"].replace("script.", ""),
                    )
                    time.sleep(3)
                    PA.plex_clients = PA.server.clients()
                    if PA.remote_server:
                        PA.update_remote_devices()
                    time.sleep(2)
                    device = fuzzy(
                        command["device"] or default_device, PA.plex_client_names
                    )
                    if aliases:
                        alias = fuzzy(
                            command["device"] or default_device, PA.alias_names
                        )
                    attempts += 1

        # If the fuzzy score is less than 60, we can't find the device.
        if alias[1] < 60 and device[1] < 60:
            _LOGGER.warning(
                '{0} {1}: "{2}"'.format(
                    localize["cast_device"].capitalize(),
                    localize["not_found"],
                    command["device"].title(),
                )
            )
            _LOGGER.debug("Device Score: %s", device[1])
            _LOGGER.debug("Devices: %s", str(devices))

            if aliases:
                _LOGGER.debug("Alias Score: %s", alias[1])
                _LOGGER.debug("Aliases: %s", str(PA.alias_names))
            return

        # Get the name of the highest scoring item between alias and device.
        # Make player = the Cast device or client name.
        name = aliases[alias[0]] if alias[1] > device[1] else device[0]
        player = PA.chromecasts[name] if name in PA.chromecast_names else name
        client = isinstance(player, str)

        # If player is a Plex client, find it with title or machine ID.
        if client:
            for c in PA.plex_clients:
                if c.title == player or c.machineIdentifier == player:
                    player = c
                    break

        try:
            player.connect()
        except:
            _LOGGER.warning(
                '{0} {1}: "{2}"'.format(
                    localize["cast_device"].capitalize(),
                    localize["not_found"],
                    command["device"].title(),
                )
            )
            return

        # Remote control operations.
        if command["control"]:
            control = command["control"]
            if client:
                controller = player
            else:
                controller = PlexController()
                player.register_handler(controller)
                player.wait()
            if control == "play":
                controller.play()
            elif control == "pause":
                controller.pause()
            elif control == "stop":
                controller.stop()
            elif control == "jump_forward":
                controller.stepForward()
            elif control == "jump_back":
                controller.stepBack()
            elif control == "skip":
                controller.next()
            elif control == "previous":
                controller.previous()
            return

        # Look for the requested media and apply user's filters (onDeck, unwatched, etc.) to them.
        try:
            result = find_media(command, command["media"], PA.lib)
            media = filter_media(PA, command, result["media"], result["library"])
        except Exception:
            error = media_error(command, localize)
            if tts_errors:
                tts = gTTS(error, lang=lang)
                tts.save(dir + "error.mp3")
                if not client:
                    player.wait()
                    media_con = player.media_controller
                    mp3 = get_url(hass) + "/local/plex_assist_tts/error.mp3"
                    media_con.play_media(mp3, "audio/mpeg")
                    media_con.block_until_active()
                    return
        _LOGGER.debug("Media: %s", str(media))

        # Set the offset if media already in progress. Clients use seconds Cast devices use milliseconds.
        # Cast devices always start 5 secs before offset, but we subtract the 5 for Clients.
        if getattr(media, "viewOffset", 0) > 10 and not command["random"]:
            offset = media.viewOffset - 5 if client else media.viewOffset / 1000

        # If it's an episode create a playqueue of the whole show and start on the selected episode.
        if getattr(media, "TYPE", None) == "episode":
            media = PA.server.createPlayQueue(media.show().episodes(), startItem=media)

        # Play the selected media on the selected device.
        if client:
            _LOGGER.debug("Client: %s", player)
            if isinstance(media, list):
                media = PA.server.createPlayQueue(media)
            player.playMedia(media, offset=offset)
        else:
            _LOGGER.debug("Cast: %s", player.name)
            plex_c = PlexController()
            player.register_handler(plex_c)
            player.wait()
            plex_c.block_until_playing(media, offset=offset)

    hass.services.async_register(DOMAIN, "command", handle_input)
    return True
