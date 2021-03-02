from datetime import datetime
from functools import lru_cache


class PlexAssistant:
    def __init__(self, server, start_script_keys):
        self.server = server
        self.library = self.server.library
        self.devices = {}
        self.start_script_keys = start_script_keys
        self.tv_id = self.get_section_id("show")
        self.movie_id = self.get_section_id("movie")
        self.music_id = self.get_section_id("artist")

    @property
    def device_names(self):
        names = list(self.devices.keys()) + self.start_script_keys
        return list(dict.fromkeys(names))

    @property
    def section_id(self):
        return {
            "movie": self.movie_id,
            "show": self.tv_id,
            "season": self.tv_id,
            "episode": self.tv_id,
            "artist": self.music_id,
            "album": self.music_id,
            "track": self.music_id,
        }

    @property
    @lru_cache()
    def media(self):
        media_items = {"all_titles": []}
        for item in ["show", "movie", "artist", "album", "track"]:
            media_items[f"{item}_titles"] = [x.title for x in self.library.search(libtype=item, sort="addedAt:desc")]
            media_items["all_titles"] += media_items[f"{item}_titles"]
        media_items["playlist_titles"] = [x.title for x in self.server.playlists()]
        media_items["updated"] = datetime.now()
        return media_items

    def get_section_id(self, section):
        section = self.library.search(libtype=section, limit=1)
        return None if not section else section[0].librarySectionID
