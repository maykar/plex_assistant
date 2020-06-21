"""
Plex Assistant is a component for Home Assistant to add control of Plex to
Google Assistant with a little help from IFTTT or DialogFlow.

Play to Google Cast devices or Plex Clients using fuzzy searches for media and
cast device names.

https://github.com/maykar/plex_assistant
"""

from homeassistant.helpers.network import get_url
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

DOMAIN = "plex_assistant"
CONF_URL = "url"
CONF_TOKEN = "token"
CONF_DEFAULT_CAST = "default_cast"
CONF_LANG = "language"
CONF_TTS_ERROR = "tts_errors"
CONF_ALIASES = "aliases"
CONF_CAST_DELAY = "cast_delay"

CONFIG_SCHEMA = vol.Schema({DOMAIN: {
    vol.Required(CONF_URL): cv.url,
    vol.Required(CONF_TOKEN): cv.string,
    vol.Optional(CONF_DEFAULT_CAST): cv.string,
    vol.Optional(CONF_CAST_DELAY, default={}): vol.Any(dict),
    vol.Optional(CONF_LANG, default='en'): cv.string,
    vol.Optional(CONF_TTS_ERROR, default=True): cv.boolean,
    vol.Optional(CONF_ALIASES, default={}): vol.Any(dict),
}}, extra=vol.ALLOW_EXTRA)


class PA:
    """ Hold our libraries, devices, etc. """
    plex = None
    server = None
    lib = {}
    devices = {}
    device_names = []
    clients = {}
    client_names = []
    client_sensor = []
    alias_names = []
    attr_update = True
    running = False
    sensor_updating = False


def setup(hass, config):
    """Called when Home Assistant is loading our component."""
    import logging
    import os

    from gtts import gTTS
    from plexapi.server import PlexServer
    from pychromecast import get_chromecasts
    from pychromecast.controllers.plex import PlexController

    from .helpers import (cc_callback, find_media, fuzzy, get_libraries,
                          media_error, play_media, video_selection)
    from .localize import LOCALIZE
    from .process_speech import process_speech
    from datetime import datetime

    _LOGGER = logging.getLogger(__name__)

    conf = config[DOMAIN]
    base_url = conf.get(CONF_URL)
    token = conf.get(CONF_TOKEN)
    default_cast = conf.get(CONF_DEFAULT_CAST)
    lang = conf.get(CONF_LANG)
    tts_error = conf.get(CONF_TTS_ERROR)
    aliases = conf.get(CONF_ALIASES)
    cast_delay = conf.get(CONF_CAST_DELAY)

    localize = LOCALIZE[lang] if lang in LOCALIZE.keys() else LOCALIZE['en']

    directory = hass.config.path() + '/www/plex_assist_tts/'
    if tts_error and not os.path.exists(directory):
        os.makedirs(directory, mode=0o777)

    get_chromecasts(blocking=False, callback=cc_callback)
    PA.server = PlexServer(base_url, token)
    PA.plex = PA.server.library
    PA.lib = get_libraries(PA.plex)
    PA.alias_names = list(aliases.keys()) if aliases else []

    def handle_input(call):
        if not call.data.get("command").strip():
            _LOGGER.warning(localize["no_call"])
            return

        PA.running = True

        if not PA.sensor_updating:
            PA.attr_update = True
            get_chromecasts(blocking=False, callback=cc_callback)

        cast = None
        client = False
        speech_error = False

        command = process_speech(
            call.data.get("command").lower(),
            localize,
            default_cast,
            PA
        )

        if not command["control"]:
            _LOGGER.debug({i: command[i] for i in command if i != 'library'})

        if PA.lib["updated"] < PA.plex.search(sort="addedAt:desc", limit=1)[0].addedAt:
            PA.lib = get_libraries(PA.plex)

        PA.device_names = list(PA.devices.keys())

        try:
            devices = PA.device_names + PA.client_names + PA.client_ids
            device = fuzzy(command["device"] or default_cast, devices)
            alias = fuzzy(command["device"] or default_cast, PA.alias_names)
            if alias[1] < 75 and device[1] < 75:
                raise Exception()
            name = aliases[alias[0]] if alias[1] > device[1] else device[0]
            cast = PA.devices[name] if name in PA.device_names else name
            client = isinstance(cast, str)
            if client:
                client_device = next(
                    c for c in PA.clients if c.title == cast or c.machineIdentifier == cast)
                cast = client_device
        except Exception:
            error = "{0} {1}: \"{2}\"".format(
                localize["cast_device"].capitalize(),
                localize["not_found"],
                command["device"].title()
            )
            _LOGGER.warning(error)
            return

        if command["control"]:
            control = command["control"]
            if client:
                cast.proxyThroughServer()
                plex_c = PA.server.client(cast)
            else:
                plex_c = PlexController()
                cast.wait()
                cast.register_handler(plex_c)
            if control == "play":
                plex_c.play()
            elif control == "pause":
                plex_c.pause()
            elif control == "stop":
                plex_c.stop()
            elif control == "jump_forward":
                plex_c.stepForward()
            elif control == "jump_back":
                plex_c.stepBack()
            return

        try:
            result = find_media(command, command["media"], PA.lib)
            media = video_selection(command, result["media"],
                                    result["library"])
        except Exception:
            error = media_error(command, localize)
            if tts_error:
                tts = gTTS(error, lang=lang)
                tts.save(directory + 'error.mp3')
                speech_error = True
            _LOGGER.warning(error)

        if speech_error and not client:
            cast.wait()
            med_con = cast.media_controller
            mp3 = get_url(hass) + "/local/plex_assist_tts/error.mp3"
            med_con.play_media(mp3, 'audio/mpeg')
            med_con.block_until_active()
            return

        _LOGGER.debug("Media: %s", str(media))

        if client:
            _LOGGER.debug("Client: %s", cast)
            cast.proxyThroughServer()
            plex_c = cast
            plex_c.playMedia(media)
        else:
            _LOGGER.debug("Cast: %s", cast.name)
            delay = 6
            if call.data.get("cast_delay") or call.data.get("cast_delay") == 0:
                delay = call.data.get("cast_delay")
            elif cast.name in cast_delay.keys():
                delay = cast_delay[cast.name]
            plex_c = PlexController()
            plex_c.namespace = 'urn:x-cast:com.google.cast.media'
            cast.register_handler(plex_c)
            cast.wait()
            play_media(float(delay), cast, plex_c, media)

        PA.running = False

    hass.services.register(DOMAIN, "command", handle_input)
    return True
