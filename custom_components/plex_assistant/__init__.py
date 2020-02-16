"""
Plex Assistant is a component for Home Assistant to add control of Plex to
Google Assistant. Play to chromecast from Plex using fuzzy searches for media
and cast device name.
"""
import logging
import time

from plexapi.server import PlexServer
from pychromecast.controllers.plex import PlexController

from .localize import LOCALIZE
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
    base_url = config[DOMAIN].get(CONF_URL)
    token = config[DOMAIN].get(CONF_TOKEN)
    default_cast = config[DOMAIN].get(CONF_DEFAULT_CAST)
    # LANGUAGE = config[DOMAIN].get(CONF_LANG)

    PA.setup(PA, PlexServer(base_url, token).library)

    def handle_input(call):
        command = process_speech(
            call.data.get("command").lower(),
            PA.lib,
            LOCALIZE["en"]  # localize[LANGUAGE] or localize["en"]
        )

        if PA.lib["updated"] < PA.plex.search(sort="addedAt:desc")[0].addedAt:
            PA.lib = get_libraries(PA.plex)

        if not command["ondeck"]:
            result = find_media(command, command["media"], PA.lib)
            media = PA.plex.section(
                result["library"].title).get(result["media"])
            media = video_selection(command, media)
        elif command["library"]:
            media = PA.plex.section(command["library"].title).onDeck()[0]
        else:
            media = PA.plex.onDeck()[0]

        name = fuzzy(command["chromecast"] or default_cast, PA.device_names)[0]
        cast = next(CC for CC in PA.devices if CC.device.friendly_name == name)

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
