import re


def get_season_episode_num(str, sea_ep):
    match = re.search(r"(?x)(?:"+sea_ep+r"|^)\s*(\d+)", str)
    if match:
        return match.group(1)


def process_speech(command, lib):
    latest = False
    unwatched = False
    ondeck = False
    library = None
    episode = ""
    season = ""
    media = ""
    chromecast = ""
    season = ""

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
    if "unwatched" in command:
        unwatched = True
        command = (
            command.replace("unwatched episode of", "")
            .replace("unwatched episodes of", "")
            .replace("unwatched", "")
        )
    if "on deck" or "ondeck" in command:
        ondeck = True
        if "tv" or "show" in command:
            library = lib["shows"]
        if "movie" in command:
            library = lib["movies"]
        command = (
            command.replace("ondeck movies", "")
            .replace("on deck movies", "")
            .replace("ondeck movie", "")
            .replace("on deck movie", "")
            .replace("ondeck tv shows", "")
            .replace("on deck tv shows", "")
            .replace("ondeck tv show", "")
            .replace("on deck tv show", "")
            .replace("ondeck show", "")
            .replace("on deck show", "")
            .replace("ondeck shows", "")
            .replace("on deck shows", "")
            .replace("ondeck tv", "")
            .replace("on deck tv", "")
            .replace("ondeck", "")
            .replace("on deck", "")
        )

    if "season number" in command:
        library = lib["shows"]
        season = get_season_episode_num(command, "season number")
        command = (
            command.replace("season number " + season + " of", "")
            .replace("season number " + season, "")
        )
    if "season" in command:
        library = lib["shows"]
        season = get_season_episode_num(command, "season")
        command = (
            command.replace("season " + season + " of", "")
            .replace("season " + season, "")
            .replace("season", "")
        )
    if "episode number" in command:
        library = lib["shows"]
        episode = get_season_episode_num(command, "episode number")
        command = (
            command.replace("episode number " + episode + " of", "")
            .replace("episode number " + episode, "")
        )
    if "episode" in command:
        library = lib["shows"]
        episode = get_season_episode_num(command, "episode")
        command = (
            command.replace("episode " + episode + " of", "")
            .replace("episode " + episode, "")
            .replace("episode of", "")
            .replace("episode", "")
        )

    if "play movie" in command or "the movie" in command:
        library = lib["movies"]
        command = (
            command.replace("the movie", "")
            .replace("movie", "")
        )
    if "play show" in command or "play tv" in command:
        library = lib["shows"]
        command = (
            command.replace("tv show", "")
            .replace("show", "")
            .replace("tv", "")
        )

    if "play" in command and "on the" in command:
        command = command.split("on the")
        media = command[0].replace("play", "")
        chromecast = command[1]
    elif "play" in command:
        media = command.replace("play", "")

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
