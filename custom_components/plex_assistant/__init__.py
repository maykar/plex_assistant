"""
Plex Assistant is a component for Home Assistant to add control of Plex to
Google Assistant. Play to chromecast from Plex using fuzzy searches for media
and cast device name.
"""
import logging
import time

from plexapi.server import PlexServer
from pychromecast.controllers.plex import PlexController

from .localize import localize
from .plex_assistant import PlexAssistant as PA
from .plex_assistant import find_media, fuzzy, get_libraries, video_selection
from .process_speech import process_speech

_LOGGER = logging.getLogger(__name__)

DOMAIN = "plex_assistant"
CONF_URL = "url"
CONF_TOKEN = "token"
CONF_DEFAULT_CAST = "default_cast"
# CONF_LANG = "language"


def setup(hass, config):
    BASEURL = config[DOMAIN].get(CONF_URL)
    TOKEN = config[DOMAIN].get(CONF_TOKEN)
    DEFAULT_CAST = config[DOMAIN].get(CONF_DEFAULT_CAST)
    # LANGUAGE = config[DOMAIN].get(CONF_LANG)

    PA.setup(PA, PlexServer(BASEURL, TOKEN).library)

    def handle_input(call):
        INPUT = process_speech(
            call.data.get("command").lower(),
            PA.lib,
            localize["en"]  # localize[LANGUAGE] or localize["en"]
        )

        if PA.lib["updated"] < PA.plex.search(sort="addedAt:desc")[0].addedAt:
            PA.lib = get_libraries(PA.plex)

        MEDIA = INPUT["media"]
        if not INPUT["ondeck"]:
            RESULT = find_media(INPUT, MEDIA, PA.lib)
            VIDEO_ID = PA.plex.section(
                RESULT["library"].title).get(RESULT["media"])
            VIDEO_ID = video_selection(INPUT, VIDEO_ID)
        elif INPUT["library"]:
            VIDEO_ID = PA.plex.section(INPUT["library"].title).onDeck()[0]
        else:
            VIDEO_ID = PA.plex.onDeck()[0]

        DEVICES = PA.devices
        CAST_NAME = INPUT["chromecast"] or DEFAULT_CAST
        NAME = fuzzy(CAST_NAME, PA.device_names)[0]
        CAST = next(CC for CC in DEVICES if CC.device.friendly_name == NAME)

        PC = PlexController()
        CAST.wait()
        CAST.register_handler(PC)

        if CAST.status.status_text:
            CAST.quit_app()
        while CAST.status.status_text:
            time.sleep(0.001)

        PC.play_media(VIDEO_ID)
        while PC.status.player_state != 'PLAYING':
            time.sleep(0.001)
        PC.play_media(VIDEO_ID)
        PC.play()

    hass.services.register(DOMAIN, "command", handle_input)
    return True
