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
CONF_DEFAULT_CAST = "default_cast"
CONF_LANG = "language"
CONF_TTS_ERROR = "tts_errors"
REMOTE_SERVER = "remote_server"
CONF_ALIASES = "aliases"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: {
            vol.Required(CONF_URL): cv.url,
            vol.Required(CONF_TOKEN): cv.string,
            vol.Optional(CONF_DEFAULT_CAST): cv.string,
            vol.Optional(CONF_LANG, default="en"): cv.string,
            vol.Optional(CONF_TTS_ERROR, default=True): cv.boolean,
            vol.Optional(REMOTE_SERVER, default=False): cv.boolean,
            vol.Optional(CONF_ALIASES, default={}): vol.Any(dict),
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
    default_device = conf.get(CONF_DEFAULT_CAST)
    lang = conf.get(CONF_LANG)
    tts_errors = conf.get(CONF_TTS_ERROR)
    remote_server = conf.get(REMOTE_SERVER)
    aliases = conf.get(CONF_ALIASES)
    zconf = await async_get_instance(hass)
    localize = LOCALIZE[lang] if lang in LOCALIZE.keys() else LOCALIZE["en"]

    # Find or create the directory to hold TTS error MP3s.
    dir = hass.config.path() + "/www/plex_assist_tts/"
    if tts_errors and not os.path.exists(dir):
        os.makedirs(dir, mode=0o777)

    def pa_executor(zconf, url, token, aliases, remote_server):
        return PlexAssistant(zconf, url, token, aliases, remote_server)

    PA = await hass.async_add_executor_job(
        pa_executor, zconf, url, token, aliases, remote_server
    )

    # First update of sensor.
    def sensor_executor():
        time.sleep(5)
        update_sensor(hass, PA)

    await hass.async_add_executor_job(sensor_executor)

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

        if localize["controls"]["update_sensor"] in command:
            update_sensor(hass, PA)
            return

        # Return a dict of the options processed from the speech command.
        command = process_speech(command, localize, default_device, PA)

        if not command["control"]:
            _LOGGER.debug({i: command[i] for i in command if i != "library"})

        # Update libraries if the latest item was added after last lib update.
        if PA.lib["updated"] < PA.plex.search(sort="addedAt:desc", limit=1)[0].addedAt:
            PA.update_libraries()

        # Get the closest name match to device in command, fuzzy returns its name and score.
        devices = PA.chromecast_names + PA.plex_client_names + PA.plex_client_ids
        device = fuzzy(command["device"] or default_device, devices)
        if aliases:
            alias = fuzzy(command["device"] or default_device, PA.alias_names)

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

        # Remote control operations.
        if command["control"]:
            control = command["control"]
            if client:
                if not hasattr(player, "remote"):
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
        if getattr(media, "viewOffset", 0) > 10 and not result["random"]:
            offset = media.viewOffset - 5 if client else media.viewOffset / 1000

        # If it's an episode create a playqueue of the whole show and start on the selected episode.
        if getattr(media, "TYPE", None) == "episode":
            media = PA.server.createPlayQueue(media.show().episodes(), startItem=media)

        # Play the selected media on the selected device.
        if client:
            _LOGGER.debug("Client: %s", player)
            if isinstance(media, list):
                media = PA.server.createPlayQueue(media)
            if not hasattr(player, "remote"):
                player.proxyThroughServer()
            player.playMedia(media, offset=offset)
        else:
            _LOGGER.debug("Cast: %s", player.name)
            plex_c = PlexController()
            player.register_handler(plex_c)
            player.wait()
            plex_c.block_until_playing(media, offset=offset)

        update_sensor(hass, PA)

    hass.services.async_register(DOMAIN, "command", handle_input)
    return True


class PlexAssistant:
    """Class for interacting with the Plex server and devices.

    Args:
        url (str): URL to connect to server.
        token (str): X-Plex-Token used for authenication.
        zconf (Zeroconf instance): HA's shared Zeroconf instance.
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

    def __init__(self, zconf, url, token, aliases, remote_server):
        from plexapi.server import PlexServer

        self.zconf = zconf
        self.server = PlexServer(url, token)
        self.token = token
        self.resources = None
        self.remote_server = remote_server
        self.chromecasts = {}
        self.update_devices()
        self.plex = self.server.library
        self.update_libraries()
        self.aliases = aliases
        self.alias_names = list(aliases.keys()) if aliases else []

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

    def update_libraries(self):
        """Update library contents, media titles, & set time updated."""
        from datetime import datetime

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

    def update_devices(self):
        """Update currently connected cast and client devices."""
        from pychromecast import get_chromecasts

        def cc_callback(chromecast):
            self.chromecasts[chromecast.device.friendly_name] = chromecast

        get_chromecasts(
            blocking=False, callback=cc_callback, zeroconf_instance=self.zconf
        )
        self.plex_clients = self.server.clients()

        if self.remote_server:
            self.update_remote_devices()

    def update_remote_devices(self):
        """Create clients from plex.tv remote endpoint."""
        from plexapi.client import PlexClient

        def setattrs(_self, **kwargs):
            for k, v in kwargs.items():
                setattr(_self, k, v)

        self.resources = None
        remote_client = None

        try:
            self.resources = self.server.myPlexAccount().resources()
        except Exception:
            _LOGGER.warning("Remote endpoint plex.tv not responding. Try again later.")

        if self.resources is None:
            return

        for rc in [r for r in self.resources if r.presence and r.publicAddressMatches]:
            if rc.name not in self.plex_client_names:
                if rc.product == "Plex Media Server":
                    continue
                for connection in [c for c in rc.connections if c.local]:
                    remote_client = PlexClient(
                        server=self.server,
                        baseurl=connection.httpuri,
                        token=self.token,
                    )
                    setattrs(
                        remote_client,
                        machineIdentifier=rc.clientIdentifier,
                        version=rc.productVersion,
                        address=connection.address,
                        product=rc.product,
                        port=connection.port,
                        title=rc.name,
                        remote=True,
                    )
                    self.plex_clients.append(remote_client)
