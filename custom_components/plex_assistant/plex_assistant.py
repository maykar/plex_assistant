import logging
from datetime import datetime

from fuzzywuzzy import fuzz
from fuzzywuzzy import process as fw
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
        "movie_titles": [
            movie.title for movie in PLEX.sectionByID(movies.key).all()
        ],
        "shows": shows,
        "show_titles": [
            show.title for show in PLEX.sectionByID(shows.key).all()
        ],
        "updated": datetime.now(),
    }


def fuzzy(media, lib, scorer=fuzz.QRatio):
    return fw.extractOne(media, lib, scorer=scorer)


def video_selection(INPUT, VIDEO_ID):
    if INPUT["season"] and INPUT["episode"]:
        return VIDEO_ID.episode(season=int(
            INPUT["season"]), episode=int(INPUT["episode"]))
    elif INPUT["season"]:
        VIDEO_ID = VIDEO_ID.season(title=int(INPUT["season"]))

    if INPUT["unwatched"]:
        if VIDEO_ID.type == "season":
            return list(filter(lambda x: not x.isWatched, VIDEO_ID))[0]
        return VIDEO_ID.unwatched()[0]
    elif INPUT["latest"]:
        return VIDEO_ID.episodes()[-1]
    else:
        return VIDEO_ID


def find_media(selected, media, lib):
    if selected["library"]:
        if selected["library"].type == 'show':
            section = "show_titles"
        else:
            section = "movie_titles"
        result = fuzzy(media, lib[section], fuzz.WRatio)[0]
        library = selected["library"]
    else:
        show_test = fuzzy(media, lib["show_titles"], fuzz.WRatio)
        movie_test = fuzzy(media, lib["movie_titles"], fuzz.WRatio)
        library = lib["shows"]
        if show_test and not movie_test:
            result = show_test[0]
        elif movie_test and not show_test:
            result = movie_test[0]
            library = lib["movies"]
        elif show_test[1] > movie_test[1]:
            result = show_test[0]
        else:
            result = movie_test[0]
            library = lib["movies"]
    return {"media": result, "library": library}


class PlexAssistant:
    plex = None
    lib = {}
    devices = []
    device_names = []

    def setup(self, plex):
        self.plex = plex
        self.lib = get_libraries(plex)
        get_chromecasts(blocking=False, callback=cc_callback)
