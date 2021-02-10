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
        movies = self.library.search(libtype="movie", sort="addedAt:desc")
        shows = self.library.search(libtype="show", sort="addedAt:desc")

        self.media = {
            "movies": movies,
            "movie_titles": [movie.title for movie in movies],
            "shows": shows,
            "show_titles": [show.title for show in shows],
            "updated": datetime.now(),
        }
