"""
Plex Assistant is a component for Home Assistant to add control of Plex to
Google Assistant with a little help from IFTTT. Play to chromecast from
Plex using fuzzy searches for media and cast device name.

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

CONFIG_SCHEMA = vol.Schema({DOMAIN: {
    vol.Required(CONF_URL): cv.url,
    vol.Required(CONF_TOKEN): cv.string,
    vol.Optional(CONF_DEFAULT_CAST): cv.string,
    vol.Optional(CONF_LANG, default='en'): cv.string,
    vol.Optional(CONF_TTS_ERROR, default=True): cv.boolean,
}}, extra=vol.ALLOW_EXTRA)


class PA:
    """ Hold our libraries, devices, etc. """
    plex = None
    lib = {}
    devices = []
    device_names = []


def setup(hass, config):
    """Called when Home Assistant is loading our component."""
    import logging
    import os
    import time

    from gtts import gTTS
    from plexapi.server import PlexServer
    from pychromecast import get_chromecasts
    from pychromecast.controllers.plex import PlexController

    from .helpers import (cc_callback, find_media, fuzzy, get_libraries,
                          media_error, video_selection)
    from .localize import localize
    from .process_speech import process_speech

    conf = config[DOMAIN]
    base_url = conf.get(CONF_URL)
    token = conf.get(CONF_TOKEN)
    default_cast = conf.get(CONF_DEFAULT_CAST)
    language = conf.get(CONF_LANG)
    tts_error = conf.get(CONF_TTS_ERROR)

    if language in localize.keys():
        localize = localize[language]
    else:
        localize = localize['en']

    directory = hass.config.path() + '/www/plex_assist_tts/'
    if tts_error:
        if not os.path.exists(directory):
            os.makedirs(directory, mode=0o777)

    PA.plex = PlexServer(base_url, token).library
    PA.lib = get_libraries(PA.plex)
    get_chromecasts(blocking=False, callback=cc_callback)

    _LOGGER = logging.getLogger(__name__)

    def handle_input(call):
        """Handle the service call."""
        command = process_speech(
            call.data.get("command").lower(),
            PA.lib,
            localize,
            default_cast
        )

        _LOGGER.debug(command)

        """ Update lib if last added item was after the last lib update. """
        if PA.lib["updated"] < PA.plex.search(sort="addedAt:desc")[0].addedAt:
            PA.lib = get_libraries(PA.plex)

        speech_error = False
        try:
            if not command["ondeck"]:
                result = find_media(command, command["media"], PA.lib)
                media = PA.plex.section(
                    result["library"].title).get(result["media"])
                media = video_selection(command, media)
            elif command["library"]:
                media = PA.plex.section(command["library"].title).onDeck()[0]
            else:
                media = PA.plex.onDeck()[0]
        except Exception:
            error = media_error(command, localize)
            if tts_error:
                tts = gTTS(error, lang=language)
                tts.save(directory + 'error.mp3')
                speech_error = True
            _LOGGER.warning(error)

        cast = None
        try:
            name = fuzzy(command["chromecast"] or default_cast,
                         PA.device_names)[0]
            cast = next(
                CC for CC in PA.devices if CC.device.friendly_name == name
            )
        except Exception:
            _LOGGER.warning("%s %s.") % (localize["cast_device"].capitalize(),
                                         localize["not_found"])
            return

        if speech_error:
            cast.wait()
            mc = cast.media_controller
            mp3 = hass.config.api.base_url + "/local/plex_assist_tts/error.mp3"
            mc.play_media(mp3, 'audio/mpeg')
            mc.block_until_active()
            return

        _LOGGER.debug(media)
        _LOGGER.debug(cast)

        plex_c = PlexController()
        cast.wait()
        cast.register_handler(plex_c)

        if cast.status.status_text:
            cast.quit_app()
        while cast.status.status_text:
            time.sleep(0.001)

        plex_c.play_media(media)
        while plex_c.status.player_state != 'PLAYING':
            time.sleep(0.001)
        plex_c.play_media(media)
        plex_c.play()

    hass.services.register(DOMAIN, "command", handle_input)
    return True
