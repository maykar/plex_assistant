from .helpers import (_find, _remove, get_library, get_media_and_device,
                      get_season_episode_num)


def process_speech(command, lib, localize, default_cast):
    """ Find and return all options found in the command string """
    latest = False
    unwatched = False
    ondeck = False
    library = None
    episode = ""
    season = ""

    for start in localize["play_start"]:
        if command.startswith(start):
            library = get_library(start, lib, localize)
            command = command.replace(start, "")

    if _find(localize["ondeck"], command):
        ondeck = True
        library = get_library(command, lib, localize)
        command = _remove(localize["ondeck"], command)

    if _find(localize["latest"], command):
        latest = True
        library = lib["shows"]
        command = _remove(localize["latest"], command)

    if _find(localize["unwatched"], command):
        unwatched = True
        command = _remove(localize["unwatched"], command)

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

    result = get_media_and_device(
        localize, command, lib, library, default_cast)

    return {
        "media": result["media"],
        "chromecast": result["chromecast"],
        "season": season,
        "episode": episode,
        "latest": latest,
        "unwatched": unwatched,
        "library": library,
        "ondeck": ondeck,
    }
