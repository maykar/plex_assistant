import logging
import re

from .plex_assistant import PlexAssistant, fuzzy

_LOGGER = logging.getLogger(__name__)


def get_season_episode_num(command, item):
    command = command.strip()
    phrase = ""
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


def convert_ordinals(command, item, ordinals):
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


def media_or_device(command, media_list):
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


def get_library(phrase, lib, localize):
    if any(word in phrase for word in localize["shows"]):
        return lib["shows"]
    elif any(word in phrase for word in localize["movies"]):
        return lib["movies"]
    return None


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
        _LOGGER.warning("Commands should start with %s", localize["play"])

    tv_strings = [localize["tv"], localize["show"], localize["shows"]]
    movie_strings = [localize["movie"], localize["movies"]]

    for start in localize["play_start"]:
        if command.startswith(start):
            library = get_library(start, lib, localize)
            command = command.replace(start, "")

    if find(localize["ondeck"], command):
        ondeck = True
        library = get_library(command, lib, localize)
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
                is_cast = media_or_device(command, lib["show_titles"])
            elif library == lib["movies"]:
                is_cast = media_or_device(command, lib["movie_titles"])
            else:
                is_cast = media_or_device(
                    command, lib["movie_titles"] + lib["show_titles"])
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
