import logging
from fuzzywuzzy import fuzz
from fuzzywuzzy import process as fw
from datetime import datetime
from pychromecast import get_chromecasts

_LOGGER = logging.getLogger(__name__)


def cc_callback(chromecast):
    PlexAssistant.device_names.append(chromecast.device.friendly_name)
    PlexAssistant.devices.append(chromecast)


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


def fuzzy(media, lib, scorer=fuzz.QRatio):
    return fw.extractOne(media, lib, scorer=scorer)


def video_selection(INPUT, VIDEO_ID):
    if INPUT["season"] and INPUT["episode"]:
        VIDEO_ID = VIDEO_ID.episode(season=int(
            INPUT["season"]), episode=int(INPUT["episode"]))
    elif INPUT["season"]:
        VIDEO_ID = VIDEO_ID.season(title=int(INPUT["season"]))
    elif INPUT["unwatched"]:
        return VIDEO_ID.unwatched()[0]
    elif INPUT["latest"]:
        return VIDEO_ID.episodes()[-1]
    else:
        return VIDEO_ID


def find_media(selected, media, lib):
    if selected["library"]:
        if selected["library"].type == 'show':
            SECTION = "show_titles"
        else:
            SECTION = "movie_titles"
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


class PlexAssistant:
    plex = None
    lib = {}
    devices = []
    device_names = []

    def setup(self, plex):
        self.plex = plex
        self.lib = get_libraries(plex)
        get_chromecasts(blocking=False, callback=cc_callback)
