import re
import logging
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

    match = re.search(r"(?:" + phrase + r"|^)\s*(\d+)", command)
    if match:
        command = command.replace(match.group(0), "")
        return {"match": match.group(1), "command": command}


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
        result = get_season_episode_num(command, localize["season"])
        season = result["match"]
        command = result["command"]
    if find(localize["episode"], command):
        library = lib["shows"]
        result = get_season_episode_num(command, localize["episode"])
        episode = result["match"]
        command = result["command"]

    if localize["on_the"] in command:
        command = command.split(localize["on_the"])
        media = command[0]
        chromecast = command[1]
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
