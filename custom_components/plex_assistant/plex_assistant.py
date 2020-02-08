import logging
import time
from fuzzywuzzy import fuzz
from fuzzywuzzy import process as fw
from datetime import datetime
from pychromecast import get_chromecasts

_LOGGER = logging.getLogger(__name__)

def cc_callback(chromecast):
    PlexCast.device_names.append(chromecast.device.friendly_name)
    PlexCast.devices.append(chromecast)

class PlexCast:
    plex = None
    lib = None
    devices = []
    device_names = []

    def setup(plex, self):
        self.plex = plex
        self.lib = get_libraries(plex)
        get_chromecasts(blocking=False, callback=cc_callback)


def process_speech(command, lib):
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

def get_libraries(PLEX):
    PLEX.reload()
    for section in PLEX.sections():
        if section.type == "movie":
            movies = section
        elif section.type == "show":
            shows = section
    return {
        "movies": movies,
        "movie_titles": [movie.title for movie in PLEX.sectionByID(movies.key).all()],
        "shows": shows,
        "show_titles": [show.title for show in PLEX.sectionByID(shows.key).all()],
        "updated": datetime.now(),
        }

def fuzzy(media, lib, scorer = fuzz.QRatio):
    return fw.extractOne(media, lib, scorer=scorer)

def video_selection(PLEX, input, library, result):
    if input["unwatched"]:
        return PLEX.section(library.title).get(result).unwatched()[0]
    elif input["latest"]:
        return PLEX.section(library.title).get(result).episodes()[-1]
    else:
        return PLEX.section(library.title).get(result)

def find_media(selected, media, lib):
    if selected["library"]:
        SECTION = "show_titles" if selected["library"].type == 'show' else "movie_titles"
        RESULT = fuzzy(media, lib[SECTION], fuzz.WRatio)[0]
        LIBRARY = selected["library"]
    else:
        show_test = fuzzy(media, lib["show_titles"], fuzz.WRatio)
        movie_test = fuzzy(media, lib["movie_titles"], fuzz.WRatio)
        LIBRARY = lib["shows"]
        if show_test and not movie_test:
            RESULT = show_test[0]
        elif movie_test and not show_test:
            RESULT = movie_test[0]
            LIBRARY = lib["movies"]
        elif show_test[1] > movie_test[1]:
            RESULT = show_test[0]
        else:
            RESULT = movie_test[0]
            LIBRARY = lib["movies"]
    return {"media": RESULT, "library": LIBRARY}
