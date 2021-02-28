import re

from .helpers import fuzzy


class ProcessSpeech:
    def __init__(self, pa, localize, command, default_cast):
        self.pa = pa
        self.command = command
        self.localize = localize
        self.device = default_cast
        self.tv_keys = localize["shows"] + localize["season"]["keywords"] + localize["episode"]["keywords"]
        self.music_keys = localize["music"] + localize["artists"] + localize["albums"] + localize["tracks"]
        self.random = False
        self.control = None
        self.library = None
        self.media = None
        self.process_command()

    @property
    def results(self):
        options = [
            "media",
            "device",
            "season",
            "episode",
            "latest",
            "unwatched",
            "random",
            "ondeck",
            "control",
            "library",
        ]
        return {option: getattr(self, option, None) for option in options}

    def process_command(self):
        controls = self.localize["controls"]
        pre_command = self.command
        for control in controls:
            ctrl = [controls[control]] if isinstance(controls[control], str) else controls[control]
            for c in ctrl:
                if self.command.startswith(c):
                    control_check = self.command.replace(c, "").strip()
                    if control_check == "":
                        self.control = control
                        return
                    device = fuzzy(control_check, self.pa.device_names)
                    self.find_replace("separator")
                    if device[0] in ["watched", "deck", "on watched", "on deck"]:
                        continue
                    if device[1] > 60 and self.command.replace(device[0].lower(), "").strip() == c:
                        self.device = device[0]
                        self.control = control
                        return
        self.command = pre_command

        self.library = self.get_library()
        self.find_replace("play_start")

        for item in ["random", "latest", "unwatched", "ondeck"]:
            setattr(self, item, self.find_replace(item))

        for item in ["season", "episode"]:
            if self.find_replace(item, False):
                self.library = "show"
                setattr(self, item, self.get_season_episode_num(self.localize[item]))
                self.find_replace(item)

        for item in ["artist", "album", "track"]:
            if self.find_replace(f"music_{item}"):
                self.library = item

        self.get_media_and_device()

    def get_library(self):
        cmd = self.command
        for device in self.pa.device_names:
            if device.lower() in cmd:
                cmd = cmd.replace(device.lower(), "")

        for item in ["shows", "movies", "artists", "albums", "tracks", "playlists"]:
            if any(word in cmd for word in self.localize[item]):
                return item[:-1]

        if any(word in cmd for word in self.music_keys):
            return "track"
        if any(word in cmd for word in self.tv_keys):
            return "episode"

    def is_device(self, media_list, separator):
        split = self.command.split(separator)
        full_score = fuzzy(self.command, media_list)[1]
        split_score = fuzzy(self.command.replace(split[-1], "")[0], media_list)[1]
        cast_score = fuzzy(split[-1], self.pa.device_names)[1]
        return full_score < split_score or full_score < cast_score

    def clear_generic(self):
        self.find_replace("movies")
        self.find_replace("playlists")
        for key in self.music_keys + self.tv_keys:
            self.command = self.command.replace(key, "")

    def get_media_and_device(self):
        for separator in self.localize["separator"]["keywords"]:
            if separator in self.command:
                self.find_replace("separator", True, separator)

                if self.command.strip().startswith(separator + " "):
                    self.device = self.command.replace(separator, "").strip()
                    return

                separator = f" {separator} "
                if separator in self.command:
                    for item in ["show", "movie", "artist", "album", "track", "playlist", "all"]:
                        if item == "all" or self.library == item:
                            self.device = self.is_device(self.pa.media[f"{item}_titles"], separator)

                    if self.device:
                        split = self.command.split(separator)
                        self.command = self.command.replace(separator + split[-1], "")
                        self.device = split[-1]

                self.clear_generic()

                if self.find_replace("music_separator", False) and getattr(self, "library", None) in [
                    "artist",
                    "album",
                    "track",
                    None,
                ]:
                    self.media = self.media_by_artist() or self.command

        if not getattr(self, "media", None):
            self.clear_generic()
            self.media = self.command

    def media_by_artist(self):
        for separator in self.localize["music_separator"]["keywords"]:
            if separator in self.command:
                self.find_replace("music_separator", True, separator)
                split = self.command.split(f" {separator} ")
                artist = fuzzy(split[-1], self.pa.media["artist_titles"])
                if artist[1] > 60:
                    albums = self.pa.server.search(artist[0], "album")
                    album_titles = [x.title for x in albums]
                    tracks = self.pa.server.search(artist[0], "track")
                    track_titles = [x.title for x in tracks]
                    if not self.library:
                        artist_item = fuzzy(split[0], album_titles + track_titles)
                        if artist_item[1] > 60:
                            return next((x for x in albums + tracks if artist_item[0] in getattr(x, "title", "")), None)
                    elif self.library == "album":
                        artist_item = fuzzy(split[0], album_titles)
                        if artist_item[1] > 60:
                            return next((x for x in albums if artist_item[0] in getattr(x, "title", "")), None)
                    elif self.library == "track":
                        artist_item = fuzzy(split[0], track_titles)
                        if artist_item[1] > 60:
                            return next((x for x in tracks if artist_item[0] in getattr(x, "title", "")), None)
        return self.command

    def find_replace(self, item, replace=True, replacement=""):
        item = self.localize[item]
        if isinstance(item, str):
            item = {"keywords": [item]}
        elif isinstance(item, list):
            item = {"keywords": item}

        if all(keyword not in self.command for keyword in item["keywords"]):
            return False

        if replace:
            if replacement:
                replacement = f" {replacement} "
            for keyword in item["keywords"]:
                self.command = f" {self.command} "
                for pre in item.get("pre", []):
                    self.command = self.command.replace(f"{pre} {keyword}", replacement)
                for post in item.get("post", []):
                    self.command = self.command.replace(f"{keyword} {post}", replacement)
                if keyword in self.command:
                    self.command = self.command.replace(f" {keyword} ", replacement)
                self.command = self.command.strip()
            self.command = " ".join(self.command.split())
        return True

    def convert_ordinals(self, item):
        match = ""
        matched = ""
        ordinals = self.localize["ordinals"]
        for word in item["keywords"]:
            for ordinal in ordinals.keys():
                if ordinal not in ("pre", "post") and ordinal in self.command:
                    match_before = re.search(fr"({ordinal})\s*({word})", self.command)
                    match_after = re.search(fr"({word})\s*({ordinal})", self.command)
                    if match_before:
                        match = match_before
                        matched = match.group(1)
                    if match_after:
                        match = match_after
                        matched = match.group(2)
                    if match:
                        replacement = match.group(0).replace(matched, ordinals[matched])
                        self.command = self.command.replace(match.group(0), replacement)
                        for pre in ordinals["pre"]:
                            if f"{pre} {match.group(0)}" in self.command:
                                self.command = self.command.replace(f"{pre} {match.group(0)}", replacement)
                        for post in ordinals["post"]:
                            if f"{match.group(0)} {post}" in self.command:
                                self.command = self.command.replace(f"{match.group(0)} {post}", replacement)
        return self.command.strip()

    def get_season_episode_num(self, item):
        self.command = self.convert_ordinals(item)
        phrase = ""
        number = None
        for keyword in item["keywords"]:
            if keyword in self.command:
                phrase = keyword
                for pre in item["pre"]:
                    if pre in self.command:
                        regex = fr"(\d+\s+)({pre}\s+)({phrase}\s+)"
                        if re.search(regex, self.command):
                            self.command = re.sub(regex, fr"{phrase} \1 ", self.command)
                        else:
                            self.command = re.sub(
                                fr"({pre}\s+)({phrase}\s+)(\d+\s+)",
                                fr"{phrase} \3",
                                self.command,
                            )
                            self.command = re.sub(
                                fr"({phrase}\s+)(\d+\s+)({pre}\s+)",
                                fr"{phrase} \2",
                                self.command,
                            )
                for post in item["post"]:
                    if post in self.command:
                        regex = fr"({phrase}\s+)({post}\s+)(\d+\s+)"
                        if re.search(regex, self.command):
                            self.command = re.sub(regex, fr"{phrase} \3", self.command)
                        else:
                            self.command = re.sub(
                                fr"(\d+\s+)({phrase}\s+)({post}\s+)",
                                fr"{phrase} \1",
                                self.command,
                            )
                            self.command = re.sub(
                                fr"({phrase}\s+)(\d+\s+)({post}\s+)",
                                fr" {phrase} \2",
                                self.command,
                            )
        match = re.search(fr"(\d+)\s*({phrase}|^)|({phrase}|^)\s*(\d+)", self.command)
        if match:
            number = match.group(1) or match.group(4)
            self.command = self.command.replace(match.group(0), "").strip()
        return number
