import re
from datetime import datetime

from fuzzywuzzy import fuzz
from fuzzywuzzy import process as fw

from . import PA


def cc_callback(chromecast):
    """ Callback for pychromecast's non-blocking get_chromecasts function.
    Adds all cast devices and their friendly names to PA.
    """
    PA.devices[chromecast.device.friendly_name] = chromecast
    if PA.client_update:
        PA.clients = PA.server.clients() if PA.server else []
        PA.client_names = [client.title for client in PA.clients]
        PA.client_ids = [client.machineIdentifier for client in PA.clients]
        PA.client_update = False


def get_libraries(plex):
    """ Return Plex libraries, their contents, media titles, & time updated """
    plex.reload()
    movies = plex.search(libtype="movie")
    movies.sort(key=lambda x: x.addedAt or x.updatedAt)
    shows = plex.search(libtype="show")
    shows.sort(key=lambda x: x.addedAt or x.updatedAt)

    return {
        "movies": movies,
        "movie_titles": [movie.title for movie in movies],
        "shows": shows,
        "show_titles": [show.title for show in shows],
        "updated": datetime.now(),
    }


def fuzzy(media, lib, scorer=fuzz.QRatio):
    """  Use Fuzzy Wuzzy to return highest scoring item. """
    if isinstance(lib, list) and len(lib) > 0:
        return fw.extractOne(media, lib, scorer=scorer)
    else:
        return ["", 0]


def video_selection(option, media, lib):
    """ Return media item.
    Narrow it down if season, episode, unwatched, or latest is used
    """
    if media and lib:
        media = next(m for m in lib if m.title == media)

    if option["season"] and option["episode"]:
        return media.episode(season=int(
            option["season"]), episode=int(option["episode"]))

    if option["season"]:
        media = media.season(title=int(option["season"]))

    if option["ondeck"]:
        if option["media"]:
            ondeck = PA.plex.onDeck()
            media = list(
                filter(lambda x:
                       (x.type == "movie" and x.title == media.title) or
                       (getattr(x, "show", None) and media.title == x.show().title) or
                       (getattr(media, "show", None) and media.show().title == x.show().title), ondeck))
        elif option["library"]:
            media = PA.plex.sectionByID(
                option["library"][0].librarySectionID).onDeck()
        else:
            media = PA.plex.onDeck()

    if option["unwatched"]:
        if not media and not lib:
            media = list(filter(lambda x: not x.isWatched, PA.plex.recentlyAdded()))
        elif not media:
            media = list(filter(lambda x: not x.isWatched, lib))
        else:
            media = media.unwatched()

    if option["latest"]:
        if not option["unwatched"]:
            if not media:
                media = PA.plex.recentlyAdded() if not lib else lib
                media.sort(key=lambda x: x.addedAt or x.updatedAt)
            if isinstance(media, list):
                media.sort(key=lambda x: x.addedAt or x.updatedAt)
        if media.type in ["show", "season"]:
            media = media.episodes()[-1]
        if isinstance(media, list):
            media = media[-1]

    if getattr(media, "TYPE", None) == "show":
        unWatched = media.unwatched()
        return unWatched[0] if unWatched else media
    
    if isinstance(media, list):
        media = media[0]

    return media


def find_media(selected, media, lib):
    """ Return media item and the library it resides in.
    If no library was given/found search both and find the closest title match.
    """
    result = ""
    library = ""
    if selected["library"]:
        if selected["library"][0].type == 'show':
            section = "show_titles"
        else:
            section = "movie_titles"

        result = "" if not media else fuzzy(
            media, lib[section], fuzz.WRatio)[0]
        library = selected["library"]
    else:
        if not media:
            result = ""
        else:
            show_test = fuzzy(media, lib["show_titles"], fuzz.WRatio)
            movie_test = fuzzy(media, lib["movie_titles"], fuzz.WRatio)
            if show_test[1] > movie_test[1]:
                result = show_test[0]
                library = lib["shows"]
            else:
                result = movie_test[0]
                library = lib["movies"]
    return {"media": result, "library": library}


def convert_ordinals(command, item, ordinals):
    """ Find ordinal numbers (first, second, third).
    Convert ordinals to int and replace the phrase in command string.
    Example: "third season of Friends" becomes "season 3 Friends"
    """
    match = ""
    replacement = ""
    for word in item["keywords"]:
        for ordinal in ordinals.keys():
            if ordinal not in ('pre', 'post') and ordinal in command:
                match_before = re.search(
                    r"(" + ordinal + r")\s*(" + word + r")", command)
                match_after = re.search(
                    r"(" + word + r")\s*(" + ordinal + r")", command)
                if match_before:
                    match = match_before
                    matched = match.group(1)
                if match_after:
                    match = match_after
                    matched = match.group(2)
                if match:
                    replacement = match.group(0).replace(
                        matched, ordinals[matched])
                    command = command.replace(match.group(0), replacement)
                    for pre in ordinals["pre"]:
                        if "%s %s" % (pre, match.group(0)) in command:
                            command = command.replace("%s %s" % (
                                match.group(0), pre), replacement)
                    for post in ordinals["post"]:
                        if "%s %s" % (match.group(0), post) in command:
                            command = command.replace("%s %s" % (
                                match.group(0), post), replacement)
    return command.strip()


def get_season_episode_num(command, item, ordinals):
    """ Find and return season/episode number.
    Then remove keyword and number from command string.
    """
    command = convert_ordinals(command, item, ordinals)
    phrase = ""
    number = None
    for keyword in item["keywords"]:
        if keyword in command:
            phrase = keyword
            for pre in item["pre"]:
                if pre in command:
                    regex = r'(\d+\s+)(' + pre + r'\s+)(' + phrase + r'\s+)'
                    if re.search(regex, command):
                        command = re.sub(regex,
                                         "%s %s " % (phrase, r'\1'), command)
                    else:
                        command = re.sub(
                            r'(' + pre + r'\s+)(' + phrase + r'\s+)(\d+\s+)',
                            "%s %s" % (phrase, r'\3'),
                            command
                        )
                        command = re.sub(
                            r'(' + phrase + r'\s+)(\d+\s+)(' + pre + r'\s+)',
                            "%s %s" % (phrase, r'\2'),
                            command
                        )
            for post in item["post"]:
                if post in command:
                    regex = r'(' + phrase + r'\s+)(' + post + r'\s+)(\d+\s+)'
                    if re.search(regex, command):
                        command = re.sub(regex,
                                         "%s %s" % (phrase, r'\3'), command)
                    else:
                        command = re.sub(
                            r'(\d+\s+)(' + phrase + r'\s+)(' + post + r'\s+)',
                            "%s %s" % (phrase, r'\1'),
                            command
                        )
                        command = re.sub(
                            r'(' + phrase + r'\s+)(\d+\s+)(' + post + r'\s+)',
                            "%s %s" % (phrase, r'\2'), command
                        )

    match = re.search(
        r"(\d+)\s*(" + phrase + r"|^)|(" + phrase + r"|^)\s*(\d+)",
        command
    )
    if match:
        number = match.group(1) or match.group(4)
        command = command.replace(match.group(0), "").strip()

    return {"number": number, "command": command}


def _find(item, command):
    """ Return true if any of the item's keywords is in the command string. """
    return any(keyword in command for keyword in item["keywords"])


def _remove(item, command, replace=""):
    """ Remove key, pre, and post words from command string. """
    command = " " + command + " "
    if replace != "":
        replace = " " + replace + " "
    for keyword in item["keywords"]:
        if item["pre"]:
            for pre in item["pre"]:
                command = command.replace("%s %s" % (pre, keyword), replace)
        if item["post"]:
            for post in item["post"]:
                command = command.replace("%s %s" % (
                    keyword, post), replace)
        if keyword in command:
            command = command.replace(" " + keyword + " ", replace)
    return ' '.join(command.split())


def get_library(phrase, lib, localize, devices):
    """ Return the library type if the phrase contains related keywords. """
    for device in devices:
        if device.lower() in phrase:
            phrase = phrase.replace(device.lower(), "")
    tv_keywords = localize["shows"] + \
        localize["season"]["keywords"] + localize["episode"]["keywords"]
    if any(word in phrase for word in tv_keywords):
        return lib["shows"]
    elif any(word in phrase for word in localize["movies"]):
        return lib["movies"]
    return None


def is_device(command, media_list, separator):
    """ Return true if string is a cast device.
    Uses fuzzy wuzzy to score media titles against cast device names.
    """
    split = command.split(separator)
    full_score = fuzzy(command, media_list)[1]
    split_score = fuzzy(command.replace(split[-1], "")[0], media_list)[1]
    cast_score = fuzzy(split[-1], PA.device_names +
                       PA.client_names + PA.alias_names)[1]
    return full_score < split_score or full_score < cast_score


def get_media_and_device(localize, command, lib, library, default_cast):
    """ Find and return the media item and cast device. """
    media = None
    device = default_cast
    separator = localize["separator"]["keywords"][0]
    command = _remove(localize["separator"], command, separator)

    if command.strip().startswith(separator + " "):
        device = command.replace(separator, "").strip()
        return {"media": "", "device": device}

    separator = " " + separator + " "
    if separator in command:
        device = False
        if library == lib["shows"]:
            device = is_device(command, lib["show_titles"], separator)
        elif library == lib["movies"]:
            device = is_device(command, lib["movie_titles"], separator)
        else:
            device = is_device(
                command,
                lib["movie_titles"] + lib["show_titles"],
                separator
            )

        if device:
            split = command.split(separator)
            media = command.replace(separator + split[-1], "")
            device = split[-1]

    media = media if media else command
    return {"media": media, "device": device}


def media_error(command, localize):
    """ Return error string. """
    error = ""
    if command["latest"]:
        error += localize["latest"]["keywords"][0] + " "
    if command["unwatched"]:
        error += localize["unwatched"]["keywords"][0] + " "
    if command["ondeck"]:
        error += localize["ondeck"]["keywords"][0] + " "
    if command["media"]:
        error += "%s " % command["media"].capitalize()
    if command["season"]:
        error += "%s %s " % (
            localize["season"]["keywords"][0], command["season"]
        )
    if command["episode"]:
        error += "%s %s " % (
            localize["episode"]["keywords"][0], command["episode"]
        )
    error += localize["not_found"] + "."
    return error.capitalize()
