import re

from fuzzywuzzy import fuzz
from fuzzywuzzy import process as fw
from random import shuffle


def update_sensor(hass, PA):
    clients = [
        {client.title: {"ID": client.machineIdentifier, "type": client.product}}
        for client in PA.plex_clients
    ]
    devicelist = PA.chromecast_names
    state = str(len(devicelist + clients)) + " connected devices."
    attributes = {
        "Connected Devices": {
            "Cast Devices": devicelist or "None",
            "Plex Clients": clients or "None",
        },
        "friendly_name": "Plex Assistant Devices",
    }
    pa_sensor = "sensor.plex_assistant_devices"
    hass.states.async_set(pa_sensor, state, attributes)


def fuzzy(media, lib, scorer=fuzz.QRatio):
    """  Use Fuzzy Wuzzy to return highest scoring item. """
    if isinstance(lib, list) and len(lib) > 0:
        return fw.extractOne(media, lib, scorer=scorer)
    else:
        return ["", 0]


def filter_media(PA, option, media, lib):
    """Return media item.
    Narrow it down if season, episode, unwatched, or latest is used
    """
    if media and lib:
        media = next(m for m in lib if m.title == media)
    elif lib:
        media = lib

    if option["season"] and option["episode"]:
        return media.episode(
            season=int(option["season"]), episode=int(option["episode"])
        )

    if option["season"]:
        media = media.season(title=int(option["season"]))

    def get_title(item, deep=False):
        if item.type == "movie":
            return item.title
        elif getattr(item, "show", None):
            return item.show().title if deep else item.title
        return None

    if option["ondeck"]:
        if option["media"]:
            ondeck = PA.plex.onDeck()
            media = list(
                filter(
                    lambda x: (get_title(x) == media.title)
                    or (get_title(media) == x.show().title)
                    or (get_title(media, True) == x.show().title),
                    ondeck,
                )
            )
        elif option["library"]:
            media = PA.plex.sectionByID(option["library"][0].librarySectionID).onDeck()
        else:
            media = PA.plex.onDeck()

    if option["unwatched"]:
        if not media and not lib:
            media = list(filter(lambda x: not x.isWatched, PA.plex.recentlyAdded()))
        elif isinstance(media, list):
            media = list(filter(lambda x: not x.isWatched, media))
        elif getattr(media, "unwatched", None):
            media = media.unwatched()

    if option["latest"]:
        if not option["unwatched"]:
            if not media:
                if not lib:
                    tvID = PA.lib["shows"][0].librarySectionID
                    movieID = PA.lib["movies"][0].librarySectionID
                    media = (
                        PA.plex.sectionByID(tvID).recentlyAdded()
                        + PA.plex.sectionByID(movieID).recentlyAdded()
                    )
                    media.sort(key=lambda x: getattr(x, "addedAt", None), reverse=True)
                else:
                    media = PA.plex.sectionByID(
                        option["library"][0].librarySectionID
                    ).recentlyAdded()
        else:
            if getattr(media, "type", None) in ["show", "season"]:
                media = media.episodes()[-1]
            elif isinstance(media, list):
                media.sort(key=lambda x: getattr(x, "addedAt", None), reverse=True)

    if getattr(media, "TYPE", None) == "show":
        unwatched = media.unwatched()
        if option["random"] and unwatched:
            return random(unwatched)
        return unwatched[0] if unwatched else media

    if option["random"]:
        return random(media)

    return media


def random(media):
    if isinstance(media, list):
        return shuffle(media)
    elif getattr(media, "episodes", None):
        return shuffle(media.episodes())
    elif getattr(media, "TYPE", None) == "episode":
        media = shuffle(media.show().episodes())


def find_media(selected, media, lib):
    """Return media item and the library it resides in.
    If no library was given/found search both and find the closest title match.
    """
    result = ""
    library = ""
    if selected["library"]:
        if selected["library"][0].type == "show":
            section = "show_titles"
        else:
            section = "movie_titles"

        result = "" if not media else fuzzy(media, lib[section], fuzz.WRatio)[0]
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
    """Find ordinal numbers (first, second, third).
    Convert ordinals to int and replace the phrase in command string.
    Example: "third season of Friends" becomes "season 3 Friends"
    """
    match = ""
    replacement = ""
    for word in item["keywords"]:
        for ordinal in ordinals.keys():
            if ordinal not in ("pre", "post") and ordinal in command:
                match_before = re.search(
                    r"(" + ordinal + r")\s*(" + word + r")", command
                )
                match_after = re.search(
                    r"(" + word + r")\s*(" + ordinal + r")", command
                )
                if match_before:
                    match = match_before
                    matched = match.group(1)
                if match_after:
                    match = match_after
                    matched = match.group(2)
                if match:
                    replacement = match.group(0).replace(matched, ordinals[matched])
                    command = command.replace(match.group(0), replacement)
                    for pre in ordinals["pre"]:
                        if "%s %s" % (pre, match.group(0)) in command:
                            command = command.replace(
                                "%s %s" % (match.group(0), pre), replacement
                            )
                    for post in ordinals["post"]:
                        if "%s %s" % (match.group(0), post) in command:
                            command = command.replace(
                                "%s %s" % (match.group(0), post), replacement
                            )
    return command.strip()


def get_season_episode_num(command, item, ordinals):
    """Find and return season/episode number.
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
                    regex = r"(\d+\s+)(" + pre + r"\s+)(" + phrase + r"\s+)"
                    if re.search(regex, command):
                        command = re.sub(regex, "%s %s " % (phrase, r"\1"), command)
                    else:
                        command = re.sub(
                            r"(" + pre + r"\s+)(" + phrase + r"\s+)(\d+\s+)",
                            "%s %s" % (phrase, r"\3"),
                            command,
                        )
                        command = re.sub(
                            r"(" + phrase + r"\s+)(\d+\s+)(" + pre + r"\s+)",
                            "%s %s" % (phrase, r"\2"),
                            command,
                        )
            for post in item["post"]:
                if post in command:
                    regex = r"(" + phrase + r"\s+)(" + post + r"\s+)(\d+\s+)"
                    if re.search(regex, command):
                        command = re.sub(regex, "%s %s" % (phrase, r"\3"), command)
                    else:
                        command = re.sub(
                            r"(\d+\s+)(" + phrase + r"\s+)(" + post + r"\s+)",
                            "%s %s" % (phrase, r"\1"),
                            command,
                        )
                        command = re.sub(
                            r"(" + phrase + r"\s+)(\d+\s+)(" + post + r"\s+)",
                            "%s %s" % (phrase, r"\2"),
                            command,
                        )

    match = re.search(
        r"(\d+)\s*(" + phrase + r"|^)|(" + phrase + r"|^)\s*(\d+)", command
    )
    if match:
        number = match.group(1) or match.group(4)
        command = command.replace(match.group(0), "").strip()

    return {"number": number, "command": command}


def _find(item, command):
    """ Return true if any of the item's keywords is in the command string. """
    if isinstance(item, str):
        return item in command
    return any(keyword in command for keyword in item["keywords"])


def _remove(item, command, replace=""):
    """ Remove key, pre, and post words from command string. """
    if isinstance(item, str):
        item = {"keywords": [item]}
    command = " " + command + " "
    if replace != "":
        replace = " " + replace + " "
    for keyword in item["keywords"]:
        if item["pre"]:
            for pre in item["pre"]:
                command = command.replace("%s %s" % (pre, keyword), replace)
        if item["post"]:
            for post in item["post"]:
                command = command.replace("%s %s" % (keyword, post), replace)
        if keyword in command:
            command = command.replace(" " + keyword + " ", replace)
    return " ".join(command.split())


def get_library(phrase, lib, localize, devices):
    """ Return the library type if the phrase contains related keywords. """
    for device in devices:
        if device.lower() in phrase:
            phrase = phrase.replace(device.lower(), "")
    tv_keywords = (
        localize["shows"]
        + localize["season"]["keywords"]
        + localize["episode"]["keywords"]
    )
    if any(word in phrase for word in tv_keywords):
        return lib["shows"]
    elif any(word in phrase for word in localize["movies"]):
        return lib["movies"]
    return None


def is_device(PA, command, media_list, separator):
    """Return true if string is a cast device.
    Uses fuzzy wuzzy to score media titles against cast device names.
    """
    split = command.split(separator)
    full_score = fuzzy(command, media_list)[1]
    split_score = fuzzy(command.replace(split[-1], "")[0], media_list)[1]
    cast_score = fuzzy(split[-1], PA.device_names)[1]
    return full_score < split_score or full_score < cast_score


def get_media_and_device(PA, localize, command, lib, library, default_cast):
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
            device = is_device(PA, command, lib["show_titles"], separator)
        elif library == lib["movies"]:
            device = is_device(PA, command, lib["movie_titles"], separator)
        else:
            device = is_device(
                PA, command, lib["movie_titles"] + lib["show_titles"], separator
            )

        if device:
            split = command.split(separator)
            media = command.replace(separator + split[-1], "")
            device = split[-1]

    media = media or command
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
        error += "%s %s " % (localize["season"]["keywords"][0], command["season"])
    if command["episode"]:
        error += "%s %s " % (localize["episode"]["keywords"][0], command["episode"])
    error += localize["not_found"] + "."
    return error.capitalize()


def process_speech(command, localize, default_cast, PA):
    """ Find and return all options found in the command string """
    lib = PA.lib
    latest = False
    unwatched = False
    ondeck = False
    random = False
    library = None
    episode = ""
    season = ""
    device = ""

    controls = localize["controls"]
    for control in controls:
        if command.startswith(controls[control]):
            control_check = command.replace(controls[control], "").strip()
            if control_check == "":
                return {"device": device, "control": control}
            else:
                fuzz_client = fuzzy(control_check, PA.device_names)
                if fuzz_client[0] in ["watched", "deck"]:
                    device = ""
                elif fuzz_client[1] > 80 and fuzz_client[0] in PA.device_names:
                    device = fuzz_client[0]
                    return {"device": device, "control": control}

    library = get_library(command, lib, localize, PA.device_names)

    for start in localize["play_start"]:
        if command.startswith(start):
            command = command.replace(start, "")

    if _find(localize["ondeck"], command):
        ondeck = True
        command = _remove(localize["ondeck"], command)

    if _find(localize["latest"], command):
        latest = True
        command = _remove(localize["latest"], command)

    if _find(localize["unwatched"], command):
        unwatched = True
        command = _remove(localize["unwatched"], command)

    if _find(localize["random"], command):
        random = True
        command = _remove(localize["random"], command)

    if _find(localize["season"], command):
        library = lib["shows"]
        result = get_season_episode_num(
            command, localize["season"], localize["ordinals"]
        )
        season = result["number"]
        command = result["command"]

    if _find(localize["episode"], command):
        library = lib["shows"]
        result = get_season_episode_num(
            command, localize["episode"], localize["ordinals"]
        )
        episode = result["number"]
        command = result["command"]

    result = get_media_and_device(PA, localize, command, lib, library, default_cast)

    return {
        "media": result["media"],
        "device": result["device"],
        "season": season,
        "episode": episode,
        "latest": latest,
        "unwatched": unwatched,
        "random": random,
        "library": library,
        "ondeck": ondeck,
        "control": "",
    }
