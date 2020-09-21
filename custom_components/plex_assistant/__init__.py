"""
Plex Assistant is a component for Home Assistant to add control of Plex to
Google Assistant with a little help from IFTTT or DialogFlow.

Play to Google Cast devices or Plex Clients using fuzzy searches for media and
cast device names.

https://github.com/maykar/plex_assistant
"""

import homeassistant.helpers.config_validation as cv
import voluptuous as vol

DOMAIN = "plex_assistant"
CONF_URL = "url"
CONF_TOKEN = "token"
CONF_DEFAULT_CAST = "default_cast"
CONF_LANG = "language"
CONF_TTS_ERROR = "tts_errors"
CONF_ALIASES = "aliases"
CONF_SENSOR = "sensor"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: {
            vol.Required(CONF_URL): cv.url,
            vol.Required(CONF_TOKEN): cv.string,
            vol.Optional(CONF_DEFAULT_CAST): cv.string,
            vol.Optional(CONF_LANG, default="en"): cv.string,
            vol.Optional(CONF_TTS_ERROR, default=True): cv.boolean,
            vol.Optional(CONF_ALIASES, default={}): vol.Any(dict),
            vol.Optional(CONF_SENSOR, default=True): cv.boolean,
        }
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Called when Home Assistant is loading our component."""

    import os
    import time
    import logging

    from gtts import gTTS
    from pychromecast import get_chromecasts
    from pychromecast.controllers.plex import PlexController
    from homeassistant.helpers.network import get_url
    from homeassistant.components.zeroconf import async_get_instance

    from .localize import LOCALIZE
    from .process_speech import process_speech
    from .helpers import (
        find_media,
        fuzzy,
        media_error,
        video_selection,
    )

    _LOGGER = logging.getLogger(__name__)

    conf = config[DOMAIN]
    url = conf.get(CONF_URL)
    token = conf.get(CONF_TOKEN)
    default_device = conf.get(CONF_DEFAULT_CAST)
    lang = conf.get(CONF_LANG)
    tts_errors = conf.get(CONF_TTS_ERROR)
    aliases = conf.get(CONF_ALIASES)
    sensor = conf.get(CONF_SENSOR)
    zeroconf = await async_get_instance(hass)
    localize = LOCALIZE[lang] if lang in LOCALIZE.keys() else LOCALIZE["en"]

    dir = hass.config.path() + "/www/plex_assist_tts/"
    if tts_errors and not os.path.exists(dir):
        os.makedirs(dir, mode=0o777)

    def sync_class_io(url, token, aliases):
        PA = PlexAssistant(url, token, aliases)
        PA.plex_client_update()
        return PA

    PA = await hass.async_add_executor_job(sync_class_io, url, token, aliases)

    def cc_callback(chromecast):
        PA.chromecasts[chromecast.device.friendly_name] = chromecast

    get_chromecasts(blocking=False, callback=cc_callback, zeroconf_instance=zeroconf)

    def sync_sensor_io():
        if not sensor:
            return
        time.sleep(5)
        update_sensor(hass, PA, sensor)

    await hass.async_add_executor_job(sync_sensor_io)

    def handle_input(call):
        player = None
        alias = ["", 0]
        speak_error = False

        if not call.data.get("command").strip():
            _LOGGER.warning(localize["no_call"])
            return

        command = call.data.get("command").strip().lower()
        _LOGGER.debug("Command: %s", command)

        PA.plex_client_update()
        get_chromecasts(
            blocking=False, callback=cc_callback, zeroconf_instance=zeroconf
        )

        if localize["controls"]["update_sensor"] in command:
            update_sensor(hass, PA, True)
            return

        command = process_speech(command, localize, default_device, PA)

        if not command["control"]:
            _LOGGER.debug({i: command[i] for i in command if i != "library"})

        if PA.lib["updated"] < PA.plex.search(sort="addedAt:desc", limit=1)[0].addedAt:
            PA.lib = PA.get_libraries()

        devices = PA.chromecast_names + PA.plex_client_names + PA.plex_client_ids
        device = fuzzy(command["device"] or default_device, devices)

        if aliases:
            alias = fuzzy(command["device"] or default_device, PA.alias_names)

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

        name = aliases[alias[0]] if alias[1] > device[1] else device[0]
        player = PA.chromecasts[name] if name in PA.chromecast_names else name
        client = isinstance(player, str)

        if client:
            player = next(
                x
                for x in PA.plex_clients
                if x.title == player or x.machineIdentifier == player
            )

        if command["control"]:
            control = command["control"]
            if client:
                player.proxyThroughServer()
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
            return

        try:
            result = find_media(command, command["media"], PA.lib)
            media = video_selection(PA, command, result["media"], result["library"])
        except Exception:
            error = media_error(command, localize)
            if tts_errors:
                tts = gTTS(error, lang=lang)
                tts.save(dir + "error.mp3")
                speak_error = True

        if speak_error and not client:
            player.wait()
            media_con = player.media_controller
            mp3 = get_url(hass) + "/local/plex_assist_tts/error.mp3"
            media_con.play_media(mp3, "audio/mpeg")
            media_con.block_until_active()
            return

        _LOGGER.debug("Media: %s", str(media))

        if client:
            _LOGGER.debug("Client: %s", player)
            player.proxyThroughServer()
            plex_c = player
            plex_c.playMedia(media)
        else:
            _LOGGER.debug("Cast: %s", player.name)
            plex_c = PlexController()
            player.register_handler(plex_c)
            player.wait()
            plex_c.block_until_playing(media)

        update_sensor(hass, PA, sensor)

    hass.services.async_register(DOMAIN, "command", handle_input)
    return True


def update_sensor(hass, PA, sensor):
    if not sensor:
        return
    clients = [
        {client.title: {"ID": client.machineIdentifier, "type": client.product}}
        for client in PA.plex_clients
    ]
    devicelist = PA.chromecast_names
    state = str(len(devicelist + clients)) + " connected devices."
    attributes = {
        "Connected Devices": {
            "Cast Devices": devicelist or "None",
            "Plex Clients": clients or "None",
        },
        "friendly_name": "Plex Assistant Devices",
    }
    pa_sensor = "sensor.plex_assistant_devices"
    hass.states.async_set(pa_sensor, state, attributes)


class PlexAssistant:
    """Hold our libraries, devices, etc."""

    chromecasts = {}
    plex_clients = {}

    def __init__(self, url, token, aliases):
        from plexapi.server import PlexServer

        self.server = PlexServer(url, token)
        self.plex = self.server.library
        self.get_libraries()
        self.aliases = aliases
        self.alias_names = list(aliases.keys()) if aliases else []

    def get_libraries(self):
        """Return Plex libraries, lib contents, media titles, & time updated."""
        from datetime import datetime

        self.plex.reload()
        movies = self.plex.search(libtype="movie")
        movies.sort(key=lambda x: x.addedAt or x.updatedAt)
        shows = self.plex.search(libtype="show")
        shows.sort(key=lambda x: x.addedAt or x.updatedAt)

        self.lib = {
            "movies": movies,
            "movie_titles": [movie.title for movie in movies],
            "shows": shows,
            "show_titles": [show.title for show in shows],
            "updated": datetime.now(),
        }

    def plex_client_update(self):
        self.plex_clients = self.server.clients() if self.server else []

    @property
    def chromecast_names(self):
        return list(self.chromecasts.keys())

    @property
    def plex_client_names(self):
        return [client.title for client in self.plex_clients]

    @property
    def plex_client_ids(self):
        return [client.machineIdentifier for client in self.plex_clients]
