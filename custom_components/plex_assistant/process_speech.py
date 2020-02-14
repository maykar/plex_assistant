import logging
import re

from .plex_assistant import PlexAssistant, fuzzy

_LOGGER = logging.getLogger(__name__)


def get_season_episode_num(command, item):
    phrase = ""
    for keyword in item["keywords"]:
        if keyword in command:
            phrase = keyword
            for pre in item["pre"]:
                if "%s %s" % (pre, phrase) in command:
                    phrase = "%s %s" % (pre, phrase)
            for post in item["post"]:
                if "%s %s" % (phrase, post) in command:
                    phrase = "%s %s" % (phrase, post)

    match = re.search(
        r"(\d+)\s*(?:" + phrase + r"|^)|(?:" + phrase + r"|^)\s*(\d+)",
        command
    )
    if match:
        number = match.group(1) or match.group(2)
        command = command.replace(match.group(0), "")
        return {"number": number, "command": command}


def convert_ordinals(command, item, ordinals):
    for word in item["keywords"]:
        for o in ordinals.keys():
            if o not in ('pre', 'post'):
                match = re.search(
                    r"(" + o + r")\s*(?:" + word + r"|^)|" +
                    r"(?:" + word + r"|^)\s*(" + o + r")",
                    command
                )
                if match:
                    matched = match.group(1) or match.group(2)
                    replacement = match.group(0).replace(
                        matched, ordinals[matched])
                    for pre in ordinals["pre"]:
                        if "%s %s" % (pre, match.group(0)) in command:
                            command = command.replace("%s %s" % (
                                pre, match.group(0)), replacement)
                    for post in ordinals["post"]:
                        if "%s %s" % (match.group(0), post) in command:
                            command = command.replace("%s %s" % (
                                match.group(0), post), replacement)
    return command


def media_or_device(lib, command, media_list):
    combined = [media_list] + [PlexAssistant.device_names]
    test_array = [item for sublist in combined for item in sublist]
    media_test = fuzzy(command, test_array)[0]
    return media_test not in media_list


def find(item, command):
    return any(keyword in command for keyword in item["keywords"])


def replace(item, command):
    for keyword in item["keywords"]:
        if item["pre"]:
            for pre in item["pre"]:
                command = command.replace("%s %s" % (
                    pre, keyword), keyword)
        if item["post"]:
            for post in item["post"]:
                command = command.replace("%s %s" % (
                    keyword, post), keyword)
        command = command.replace(keyword, "")
    return command


def process_speech(command, lib, localize):
    latest = False
    unwatched = False
    ondeck = False
    library = None
    episode = ""
    season = ""
    media = ""
    chromecast = ""
    season = ""

    if not localize["play"] in command:
        _LOGGER.warning("Commands should start with %s" % (localize["play"]))

    tv_strings = [localize["tv"], localize["show"], localize["shows"]]
    movie_strings = [localize["movie"], localize["movies"]]

    for start in localize["play_start"]:
        if command.startswith(start):
            if any(word in start for word in movie_strings):
                library = lib["movies"]
            if any(word in start for word in tv_strings):
                library = lib["shows"]
            command = command.replace(start, "")

    if find(localize["ondeck"], command):
        ondeck = True
        if any(word in command for word in tv_strings):
            library = lib["shows"]
        if any(word in command for word in movie_strings):
            library = lib["movies"]
        command = replace(localize["ondeck"], command)

    if find(localize["latest"], command):
        latest = True
        library = lib["shows"]
        command = replace(localize["latest"], command)

    if find(localize["unwatched"], command):
        unwatched = True
        command = replace(localize["unwatched"], command)

    if find(localize["season"], command):
        library = lib["shows"]
        command = convert_ordinals(
            command, localize["season"], localize["ordinals"])
        result = get_season_episode_num(command, localize["season"])
        season = result["number"]
        command = result["command"]

    if find(localize["episode"], command):
        library = lib["shows"]
        command = convert_ordinals(
            command, localize["episode"], localize["ordinals"])
        result = get_season_episode_num(command, localize["episode"])
        episode = result["number"]
        command = result["command"]

    if localize["on_the"] in command:
        if len(command.split(localize["on_the"])) > 2:
            chromecast = command.split(localize["on_the"])[-1]
            command = command.replace("%s %s" % (
                localize["on_the"], chromecast.strip()), "")
            media = command
        else:
            is_cast = False
            if library == lib["shows"]:
                is_cast = media_or_device(lib, command, lib["show_titles"])
            elif library == lib["movies"]:
                is_cast = media_or_device(lib, command, lib["movie_titles"])
            else:
                is_cast = media_or_device(
                    lib, command, lib["movie_titles"] + lib["show_titles"])
            if is_cast:
                command = command.split(localize["on_the"])
                media = command[0]
                chromecast = command[1]
            else:
                media = command
    else:
        media = command

    return {
        "media": media.strip(),
        "chromecast": chromecast.strip(),
        "season": season,
        "episode": episode,
        "latest": latest,
        "unwatched": unwatched,
        "library": library,
        "ondeck": ondeck,
    }
