from datetime import datetime


class PlexAssistant:
    def __init__(self, server, start_script_keys):
        self.server = server
        self.library = self.server.library
        self.devices = {}
        self.media = {}
        self.start_script_keys = start_script_keys
        self.update_libraries()
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

    def update_libraries(self):
        self.library.reload()
        self.media["all_titles"] = []
        for item in ["show", "movie", "artist", "album", "track"]:
            self.media[f"{item}_titles"] = [x.title for x in self.library.search(libtype=item, sort="addedAt:desc")]
            self.media["all_titles"] += self.media[f"{item}_titles"]
        self.media["playlist_titles"] = [x.title for x in self.server.playlists()]
        self.media["updated"] = datetime.now()

    def get_section_id(self, section):
        section = self.library.search(libtype=section, limit=1)
        return None if not section else section[0].librarySectionID
