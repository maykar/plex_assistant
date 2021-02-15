import re
from .helpers import fuzzy


class ProcessSpeech:
    def __init__(self, pa, localize, command, default_cast):
        self.pa = pa
        self.command = command
        self.localize = localize
        self.library = pa.media
        self.device = default_cast
        self.library_section = None
        self.media = None
        self.control = None
        self.season = None
        self.episode = None
        self.latest = False
        self.unwatched = False
        self.random = False
        self.ondeck = False
        self.tv_keys = localize["shows"] + localize["season"]["keywords"] + localize["episode"]["keywords"]
        self.process_command()

    @property
    def results(self):
        return {
            "media": self.media,
            "device": self.device,
            "season": self.season,
            "episode": self.episode,
            "latest": self.latest,
            "unwatched": self.unwatched,
            "random": self.random,
            "library": self.library_section,
            "ondeck": self.ondeck,
            "control": self.control,
        }

    def process_command(self):
        controls = self.localize["controls"]
        pre_command = self.command
        for control in controls:
            if self.command.startswith(controls[control]):
                control_check = self.command.replace(controls[control], "").strip()
                if control_check == "":
                    self.control = control
                    return
                device = fuzzy(control_check, self.pa.device_names)
                self.find_replace("separator")
                if device[0] in ["watched", "deck", "on watched", "on deck"]:
                    continue
                elif device[1] > 60 and self.command.replace(device[0].lower(), "").strip() == controls[control]:
                    self.device = device[0]
                    self.control = control
                    return
        self.command = pre_command

        self.library_section = self.get_library()
        self.find_replace("play_start")
        self.random = self.find_replace("random")
        self.latest = self.find_replace("latest")
        self.unwatched = self.find_replace("unwatched")
        self.ondeck = self.find_replace("ondeck")

        if self.find_replace("season", False):
            self.library_section = self.library["shows"]
            self.season = self.get_season_episode_num(self.localize["season"])
        if self.find_replace("episode", False):
            self.library_section = self.library["shows"]
            self.episode = self.get_season_episode_num(self.localize["episode"])

        self.get_media_and_device()

    def get_library(self):
        cmd = self.command
        for device in self.pa.device_names:
            if device.lower() in cmd:
                cmd = cmd.replace(device.lower(), "")
        if any(word in cmd for word in self.tv_keys):
            return self.library["shows"]
        elif any(word in self.command for word in self.localize["movies"]):
            return self.library["movies"]

    def is_device(self, media_list, separator):
        split = self.command.split(separator)
        full_score = fuzzy(self.command, media_list)[1]
        split_score = fuzzy(self.command.replace(split[-1], "")[0], media_list)[1]
        cast_score = fuzzy(split[-1], self.pa.device_names)[1]
        return full_score < split_score or full_score < cast_score

    def get_media_and_device(self):
        media = None
        separator = self.localize["separator"]["keywords"][0]
        self.find_replace("separator", True, separator)

        if self.command.strip().startswith(separator + " "):
            self.device = self.command.replace(separator, "").strip()
            return
        separator = f" {separator} "
        if separator in self.command:
            if self.library_section == self.library["shows"]:
                self.device = self.is_device(self.library["show_titles"], separator)
            elif self.library_section == self.library["movies"]:
                self.device = self.is_device(self.library["movie_titles"], separator)
            else:
                self.device = self.is_device(self.library["movie_titles"] + self.library["show_titles"], separator)
            if self.device:
                split = self.command.split(separator)
                self.command = self.command.replace(separator + split[-1], "")
                self.device = split[-1]
        self.find_replace("shows")
        self.find_replace("movies")
        self.media = self.command

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
                    match_before = re.search(r"(" + ordinal + r")\s*(" + word + r")", self.command)
                    match_after = re.search(r"(" + word + r")\s*(" + ordinal + r")", self.command)
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
                            if "%s %s" % (pre, match.group(0)) in self.command:
                                self.command = self.command.replace("%s %s" % (match.group(0), pre), replacement)
                        for post in ordinals["post"]:
                            if "%s %s" % (match.group(0), post) in self.command:
                                self.command = self.command.replace("%s %s" % (match.group(0), post), replacement)
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
                        regex = r"(\d+\s+)(" + pre + r"\s+)(" + phrase + r"\s+)"
                        if re.search(regex, self.command):
                            self.command = re.sub(regex, "%s %s " % (phrase, r"\1"), self.command)
                        else:
                            self.command = re.sub(
                                r"(" + pre + r"\s+)(" + phrase + r"\s+)(\d+\s+)",
                                "%s %s" % (phrase, r"\3"),
                                self.command,
                            )
                            self.command = re.sub(
                                r"(" + phrase + r"\s+)(\d+\s+)(" + pre + r"\s+)",
                                "%s %s" % (phrase, r"\2"),
                                self.command,
                            )
                for post in item["post"]:
                    if post in self.command:
                        regex = r"(" + phrase + r"\s+)(" + post + r"\s+)(\d+\s+)"
                        if re.search(regex, self.command):
                            self.command = re.sub(regex, "%s %s" % (phrase, r"\3"), self.command)
                        else:
                            self.command = re.sub(
                                r"(\d+\s+)(" + phrase + r"\s+)(" + post + r"\s+)",
                                "%s %s" % (phrase, r"\1"),
                                self.command,
                            )
                            self.command = re.sub(
                                r"(" + phrase + r"\s+)(\d+\s+)(" + post + r"\s+)",
                                "%s %s" % (phrase, r"\2"),
                                self.command,
                            )
        match = re.search(r"(\d+)\s*(" + phrase + r"|^)|(" + phrase + r"|^)\s*(\d+)", self.command)
        if match:
            number = match.group(1) or match.group(4)
            self.command = self.command.replace(match.group(0), "").strip()
        return number
