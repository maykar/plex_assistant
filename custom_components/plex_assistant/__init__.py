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

CONFIG_SCHEMA = vol.Schema({DOMAIN: {
    vol.Required(CONF_URL): cv.url,
    vol.Required(CONF_TOKEN): cv.string,
    vol.Optional(CONF_DEFAULT_CAST): cv.string,
    vol.Optional(CONF_LANG, default='en'): cv.string,
    vol.Optional(CONF_TTS_ERROR, default=True): cv.boolean,
    vol.Optional(CONF_ALIASES): vol.Any(dict),
}}, extra=vol.ALLOW_EXTRA)


class PA:
    """ Hold our libraries, devices, etc. """
    plex = None
    server = None
    lib = {}
    devices = {}
    device_names = []
    client_names = []
    alias_names = []


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

    _LOGGER = logging.getLogger(__name__)

    conf = config[DOMAIN]
    base_url = conf.get(CONF_URL)
    token = conf.get(CONF_TOKEN)
    default_cast = conf.get(CONF_DEFAULT_CAST)
    lang = conf.get(CONF_LANG)
    tts_error = conf.get(CONF_TTS_ERROR)
    aliases = conf.get(CONF_ALIASES)

    localize = LOCALIZE[lang] if lang in LOCALIZE.keys() else LOCALIZE['en']

    directory = hass.config.path() + '/www/plex_assist_tts/'
    if tts_error and not os.path.exists(directory):
        os.makedirs(directory, mode=0o777)

    PA.server = PlexServer(base_url, token)
    PA.plex = PA.server.library
    PA.lib = get_libraries(PA.plex)
    PA.alias_names = list(aliases.keys())
    PA.client_names = [client.title for client in PA.server.clients()]
    get_chromecasts(blocking=False, callback=cc_callback)

    def handle_input(call):
        """Handle the service call."""
        if not call.data.get("command").strip():
            _LOGGER.warning(localize["no_call"])
            return

        cast = None
        client = False
        speech_error = False

        get_chromecasts(blocking=False, callback=cc_callback)
        for client in PA.server.clients():
            if client.title not in PA.client_names:
                PA.client_names.append(client.title)

        command = process_speech(
            call.data.get("command").lower(),
            localize,
            default_cast,
            PA
        )

        if not command["control"]:
            _LOGGER.debug({i: command[i] for i in command if i != 'library'})

        if PA.lib["updated"] < PA.plex.search(sort="addedAt:desc")[0].addedAt:
            PA.lib = get_libraries(PA.plex)

        try:
            devices = PA.device_names + PA.client_names + PA.alias_names
            name = fuzzy(command["device"] or default_cast, devices)[0]
            if name in PA.alias_names and aliases[name] in PA.device_names:
                cast = PA.devices[aliases[name]]
            elif name in PA.device_names:
                cast = PA.devices[name]
            elif name in PA.client_names + PA.alias_names:
                cast = aliases[name] if name in aliases else name
                client = True
        except Exception:
            error = "{0} {1}.".format(localize["cast_device"].capitalize(),
                                      localize["not_found"])
            _LOGGER.warning(error)
            return

        if command["control"]:
            control = command["control"]
            if client:
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
            mp3 = hass.config.api.base_url + "/local/plex_assist_tts/error.mp3"
            med_con.play_media(mp3, 'audio/mpeg')
            med_con.block_until_active()
            return

        _LOGGER.debug("Media: %s", str(media))

        if client:
            _LOGGER.debug("Client: %s", cast)
            plex_c = PA.server.client(cast)
            plex_c.playMedia(media)
        else:
            _LOGGER.debug("Cast: %s", cast.name)
            plex_c = PlexController()
            cast.wait()
            cast.register_handler(plex_c)
            play_media(cast, plex_c, media)

    hass.services.register(DOMAIN, "command", handle_input)
    return True
