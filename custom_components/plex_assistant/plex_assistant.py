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
        artists = self.library.search(libtype="artist", sort="addedAt:desc")
        albums = self.library.search(libtype="album", sort="addedAt:desc")
        tracks = self.library.search(libtype="track", sort="addedAt:desc")
        playlists = self.server.playlists()

        self.media = {
            "movies": movies,
            "movie_titles": [movie.title for movie in movies],
            "shows": shows,
            "show_titles": [show.title for show in shows],
            "artists": artists,
            "artist_titles": [artist.title for artist in artists],
            "albums": albums,
            "album_titles": [album.title for album in albums],
            "tracks": tracks,
            "track_titles": [track.title for track in tracks],
            "playlists": playlists,
            "playlist_titles": [playlist.title for playlist in playlists],
            "updated": datetime.now(),
        }
