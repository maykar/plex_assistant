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
        self.process_command()

    @property
    def results(self):
        results = {}
        for x in ["media", "device", "season", "episode", "latest", "unwatched", "random", "ondeck", "control", "library"]:
            results[x] = getattr(self, x, None)
        return results

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
                    elif device[1] > 60 and self.command.replace(device[0].lower(), "").strip() == c:
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
                self.library = self.pa.media["shows"]
                setattr(self, item, self.get_season_episode_num(self.localize[item]))
                self.find_replace(item)

        for item in ["artist", "album", "track", "playlist"]:
            if self.find_replace(f"music_{item}"):
                self.library = self.pa.media[f"{item}s"]

        self.get_media_and_device()

    def get_library(self):
        cmd = self.command
        for device in self.pa.device_names:
            if device.lower() in cmd:
                cmd = cmd.replace(device.lower(), "")

        if any(word in cmd for word in self.tv_keys):
            return self.pa.media["shows"]

        if any(word in cmd for word in self.music_keys):
            return self.pa.media["tracks"]

        for item in ["movies", "artists", "albums", "tracks", "playlists"]:
            if any(word in cmd for word in self.localize[item]):
                return self.pa.media[item]

    def is_device(self, media_list, separator):
        split = self.command.split(separator)
        full_score = fuzzy(self.command, media_list)[1]
        split_score = fuzzy(self.command.replace(split[-1], "")[0], media_list)[1]
        cast_score = fuzzy(split[-1], self.pa.device_names)[1]
        return full_score < split_score or full_score < cast_score

    def get_media_and_device(self):
        media = None
        for separator in self.localize["separator"]["keywords"]:
            if separator in self.command:
                self.find_replace("separator", True, separator)

                if self.command.strip().startswith(separator + " "):
                    self.device = self.command.replace(separator, "").strip()
                    return

                separator = f" {separator} "
                if separator in self.command:
                    for item in ["show", "movie", "artist", "album", "track", "playlist", "all"]:
                        if item == "all" or self.library == self.pa.media[f"{item}s"]:
                            self.device = self.is_device(self.pa.media[f"{item}_titles"], separator)

                    if self.device:
                        split = self.command.split(separator)
                        self.command = self.command.replace(separator + split[-1], "")
                        self.device = split[-1]

                self.find_replace("shows")
                self.find_replace("movies")

                for key in self.music_keys:
                    if not self.command.replace(key, ""):
                        self.command = self.command.replace(key, "")

                lib = None if not getattr(self, "library", None) else getattr(self, "library")[0]
                if self.find_replace("music_separator", False) and getattr(lib, "type", None) in ["artist", "album", "track", None]:
                    self.media = self.media_by_artist(lib) or self.command
                else:
                    self.media = self.command

    def media_by_artist(self, lib):
        artist_media = None
        for separator in self.localize["music_separator"]["keywords"]:
            if separator in self.command:
                self.find_replace("music_separator", True, separator)
                split = self.command.split(f" {separator} ")
                artist = fuzzy(split[-1], self.pa.media["artist_titles"])
                if artist[1] > 60:
                    artist_albums = self.pa.server.search(artist[0], "album")
                    artist_album_titles = [x.title for x in artist_albums]
                    artist_tracks = self.pa.server.search(artist[0], "track")
                    artist_track_tracks = [x.title for x in artist_tracks]
                    if not lib:
                        artist_media = fuzzy(split[0], artist_album_titles + artist_track_tracks)
                        if artist_media[1] > 60:
                            return next((x for x in artist_albums + artist_tracks if artist_media[0] in getattr(x, "title", "")), None)
                    elif lib.type == "album":
                        artist_media = fuzzy(split[0], artist_album_titles)
                        if artist_media[1] > 60:
                            return next((x for x in artist_albums if artist_media[0] in getattr(x, "title", "")), None)
                    elif lib.type == "track":
                        artist_media = fuzzy(split[0], artist_track_tracks)
                        if artist_media[1] > 60:
                            return next((x for x in artist_tracks if artist_media[0] in getattr(x, "title", "")), None)
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
