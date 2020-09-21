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

    import logging
    import os
    import time

    from gtts import gTTS
    from homeassistant.helpers.network import get_url
    from homeassistant.components.zeroconf import async_get_instance
    from pychromecast import get_chromecasts
    from pychromecast.controllers.plex import PlexController

    from .localize import LOCALIZE
    from .helpers import (
        find_media,
        fuzzy,
        media_error,
        video_selection,
        update_sensor,
        process_speech,
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
    zconf = await async_get_instance(hass)
    localize = LOCALIZE[lang] if lang in LOCALIZE.keys() else LOCALIZE["en"]

    # Find or create the directory to hold TTS error MP3s.
    dir = hass.config.path() + "/www/plex_assist_tts/"
    if tts_errors and not os.path.exists(dir):
        os.makedirs(dir, mode=0o777)

    def pa_executor(url, token, aliases):
        return PlexAssistant(url, token, aliases)

    PA = await hass.async_add_executor_job(pa_executor, url, token, aliases)

    def cc_callback(chromecast):
        """get_chromecasts() callback function."""
        PA.chromecasts[chromecast.device.friendly_name] = chromecast

    get_chromecasts(blocking=False, callback=cc_callback, zeroconf_instance=zconf)

    # First update of sensor.
    def sensor_executor():
        time.sleep(5)
        update_sensor(hass, PA, sensor)

    if sensor:
        await hass.async_add_executor_job(sensor_executor)

    def handle_input(call):
        player = None
        alias = ["", 0]

        PA.plex_client_update()
        get_chromecasts(blocking=False, callback=cc_callback, zeroconf_instance=zconf)

        if not call.data.get("command").strip():
            _LOGGER.warning(localize["no_call"])
            return

        command = call.data.get("command").strip().lower()
        _LOGGER.debug("Command: %s", command)

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
            for c in PA.plex_clients:
                if c.title == player or c.machineIdentifier == player:
                    player == c
                    break

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
                if not client:
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


class PlexAssistant:
    """Main class for interacting with the Plex server.

    Args:
        url (str): URL to connect to server.
        token (str): X-Plex-Token used for authenication.
        aliases (dict): Alternate names assigned to devices.

    Attributes:
        server (:class:`~plexapi.server.PlexServer`): The Plex server.
        plex: The main library for all media, recentlyAdded, onDeck, etc.
        lib (dict): All video (seperated into sections), media titles, & time last updated.
        aliases (dict): Alternate names assigned to devices.
        alias_names (list): List of alias names.
        chromecasts (dict): All connected Google cast devices.
        chromecast_names (list): List of Google cast device names.
        plex_clients (list): List of connected Plex client objects.
        plex_client_names (list): List of Plex client titles.
        plex_client_ids (list): List of Plex client machine IDs.
        device_names (list): Combined list of alias, chromecast, and plex client names.
    """

    from plexapi.server import PlexServer
    from datetime import datetime

    chromecasts = {}  # Updated on load and on call with get_chromecasts().

    def __init__(self, url, token, aliases):
        self.server = PlexServer(url, token)
        self.plex = self.server.library
        self.lib = self.get_libraries()
        self.aliases = aliases
        self.alias_names = list(aliases.keys()) if aliases else []
        self.plex_clients = self.server.clients()

    @property
    def chromecast_names(self):
        """Returns list of Chromcast names"""
        return list(self.chromecasts.keys())

    @property
    def plex_client_names(self):
        """Returns list of Plex client names"""
        return [client.title for client in self.plex_clients]

    @property
    def plex_client_ids(self):
        """Return a list of current Plex client's machine IDs."""
        return [client.machineIdentifier for client in self.plex_clients]

    @property
    def device_names(self):
        """Return list of devices and aliases names"""
        return self.chromecast_names + self.plex_client_names + self.alias_names

    def plex_client_update(self):
        """Get currently connected Plex clients."""
        self.plex_clients = self.server.clients()

    def get_libraries(self):
        """Update library contents, media titles, & set time updated."""

        self.plex.reload()
        movies = self.plex.search(libtype="movie", sort="addedAt:desc")
        shows = self.plex.search(libtype="show", sort="addedAt:desc")

        self.lib = {
            "movies": movies,
            "movie_titles": [movie.title for movie in movies],
            "shows": shows,
            "show_titles": [show.title for show in shows],
            "updated": datetime.now(),
        }
