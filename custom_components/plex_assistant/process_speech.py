from .helpers import (
    _find,
    _remove,
    get_library,
    get_media_and_device,
    get_season_episode_num,
    fuzzy,
)


def process_speech(command, localize, default_cast, PA):
    """ Find and return all options found in the command string """
    lib = PA.lib
    latest = False
    unwatched = False
    ondeck = False
    library = None
    episode = ""
    season = ""
    remote = ""
    device = ""

    devices = PA.chromecast_names + PA.plex_client_names + PA.alias_names
    controls = localize["controls"]
    for control in controls:
        if command.startswith(controls[control]):
            control_check = command.replace(controls[control], "").strip()
            if control_check == "":
                return {"device": device, "control": control}
            else:
                fuzz_client = fuzzy(control_check, devices)
                if fuzz_client[1] > 80 and fuzz_client[0] in devices:
                    device = fuzz_client[0]
                    return {"device": device, "control": control}

    library = get_library(command, lib, localize, devices)

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
        "library": library,
        "ondeck": ondeck,
        "control": "",
    }
