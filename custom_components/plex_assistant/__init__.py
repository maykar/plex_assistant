"""
Plex Assistant is a component for Home Assistant to add control of Plex to
Google Assistant. Play to chromecast from Plex using fuzzy searches for media
and cast device name.
"""
import time
import logging
from plexapi.server import PlexServer
from fuzzywuzzy import fuzz
from fuzzywuzzy import process as fw
from pychromecast.controllers.plex import PlexController
from pychromecast import get_chromecasts

_LOGGER = logging.getLogger(__name__)

DOMAIN = "plex_assistant"

CONF_URL = "url"
CONF_TOKEN = "token"
CONF_DEFAULT_CAST = "default_cast"


def setup(hass, config):
    BASEURL = config[DOMAIN].get(CONF_URL)
    TOKEN = config[DOMAIN].get(CONF_TOKEN)
    DEFAULT_CAST = config[DOMAIN].get(CONF_DEFAULT_CAST)
    PLEX = PlexServer(BASEURL, TOKEN)
    PLEX = PLEX.library

    def get_libraries():
        PLEX.reload()
        for section in PLEX.sections():
            if section.type == "movie":
                movies = section
            elif section.type == "show":
                shows = section
        return {"movies": movies, "shows": shows}

    def process_text(command, lib):
        latest = False
        unwatched = False
        library = False
        media = ""
        chromecast = ""

        if "latest episode" in command or "latest" in command:
            latest = True
            library = lib["shows"]
            command = (
                command.replace("the latest episode of", "")
                .replace("the latest episode", "")
                .replace("latest episode of", "")
                .replace("latest episode", "")
                .replace("latest", "")
            )
        if "episode" in command:
            library = lib["shows"]
            command = command.replace("episode", "")
        if "play movie" in command or "the movie" in command:
            library = lib["movies"]
            command = command.replace("movie", "").replace("the movie", "")
        if "play show" in command or "play tv" in command:
            library = lib["shows"]
            command = command.replace("show", "")
            command = command.replace("tv", "")
        if "unwatched" in command:
            unwatched = True
            command = command.replace("unwatched", "")

        if "play" in command and "on the" in command:
            command = command.split("on the")
            media = command[0].replace("play", "")
            chromecast = command[1]
        elif "play" in command:
            media = command.replace("play", "")

        return {
            "media": media.strip(),
            "chromecast": chromecast.strip(),
            "latest": latest,
            "unwatched": unwatched,
            "library": library,
        }

    def titles(lib):
        return [media.title for media in PLEX.sectionByID(lib.key).all()]

    def fuzzy(media, lib, scorer):
        return fw.extractOne(media, lib, scorer=scorer)

    def video_selection(input, library, result):
        if input["unwatched"]:
            return PLEX.section(library.title).get(result).unwatched()[0]
        elif input["latest"]:
            return PLEX.section(library.title).get(result).episodes()[-1]
        else:
            return PLEX.section(library.title).get(result)

    def handle_input(call):
        """Handle the service call."""
        COMMAND = call.data.get("command")
        LIBRARIES = get_libraries()
        INPUT = process_text(COMMAND.lower(), LIBRARIES)
        CAST_NAME = INPUT["chromecast"] or DEFAULT_CAST
        MEDIA = INPUT["media"]

        if INPUT["library"]:
            RESULT = fuzzy(MEDIA, titles(INPUT["library"]), fuzz.WRatio)[0]
            LIBRARY = INPUT["library"]
        else:
            show_test = fuzzy(MEDIA, titles(LIBRARIES["shows"]), fuzz.WRatio)
            movie_test = fuzzy(MEDIA, titles(LIBRARIES["movies"]), fuzz.WRatio)
            LIBRARY = LIBRARIES["shows"]
            if show_test and not movie_test:
                RESULT = show_test[0]
            elif movie_test and not show_test:
                RESULT = movie_test[0]
                LIBRARY = LIBRARIES["movies"]
            elif show_test[1] > movie_test[1]:
                RESULT = show_test[0]
            else:
                RESULT = movie_test[0]
                LIBRARY = LIBRARIES["movies"]

        VIDEO_ID = PLEX.section(LIBRARY.title).get(RESULT)
        DEVICES = get_chromecasts()

        CC_NAMES = []
        for CC in DEVICES: CC_NAMES.append(CC.device.friendly_name)

        NAME = fuzzy(CAST_NAME, CC_NAMES, fuzz.QRatio)[0]
        CAST = next(CC for CC in DEVICES if CC.device.friendly_name == NAME)

        VIDEO_ID = video_selection(INPUT, LIBRARY, RESULT)

        PC = PlexController()
        CAST.register_handler(PC)
        CAST.wait()

        PC.play_media(VIDEO_ID)
        while PC.status.player_state != 'PLAYING': time.sleep(0.001)
        PC.play_media(VIDEO_ID)
        PC.play()

    hass.services.register(DOMAIN, "command", handle_input)
    return True
