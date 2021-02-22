from datetime import datetime


class PlexAssistant:
    def __init__(self, server, start_script_keys):
        self.server = server
        self.library = self.server.library
        self.devices = {}
        self.media = {}
        self.start_script_keys = start_script_keys
        self.update_libraries()

    @property
    def device_names(self):
        names = list(self.devices.keys()) + self.start_script_keys
        return list(dict.fromkeys(names))

    def update_libraries(self):
        self.library.reload()
        self.media["all_titles"] = []

        for item in ["show", "movie", "artist", "album", "track"]:
            self.media[f"{item}s"] = self.library.search(libtype=item, sort="addedAt:desc")
            self.media[f"{item}_titles"] = [x.title for x in self.media[f"{item}s"]]
            self.media["all_titles"] += self.media[f"{item}_titles"]

        self.media["playlists"] = self.server.playlists()
        self.media["playlist_titles"] = [playlist.title for playlist in self.media["playlists"]]

        self.media["updated"] = datetime.now()
