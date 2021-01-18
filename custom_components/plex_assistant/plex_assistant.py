class PlexAssistant:
    """Class for interacting with the Plex server and devices.

    Args:
        url (str): URL to connect to server.
        token (str): X-Plex-Token used for authenication.
        zconf (Zeroconf instance): HA's shared Zeroconf instance.
        aliases (dict): Alternate names assigned to devices.

    Attributes:
        server (:class:`~plexapi.server.PlexServer`): The Plex server.
        plex: The main library for all media, recentlyAdded, onDeck, etc.
        lib (dict): All video (seperated into sections), media titles, & time last updated.
        aliases (dict): Alternate names assigned to devices.
        alias_names (list): List of alias names.
        chromecasts (dict): All connected Google cast devices.
        chromecast_names (list): List of Google cast device names.
        plex_clients (list): List of connected Plex client objects.
        plex_client_names (list): List of Plex client titles.
        plex_client_ids (list): List of Plex client machine IDs.
        device_names (list): Combined list of alias, chromecast, and plex client names.
    """

    def __init__(self, zconf, token, aliases, remote_server, server):
        self.zconf = zconf
        self.server = server
        self.token = token
        self.resources = None
        self.remote_server = remote_server
        self.chromecasts = {}
        self.update_devices()
        self.plex = self.server.library
        self.update_libraries()
        self.aliases = aliases
        self.alias_names = list(aliases.keys()) if aliases else []

    @property
    def chromecast_names(self):
        """Returns list of Chromcast names"""
        return list(self.chromecasts.keys())

    @property
    def plex_client_names(self):
        """Returns list of Plex client names"""
        return [client.title for client in self.plex_clients]

    @property
    def plex_client_ids(self):
        """Return a list of current Plex client's machine IDs."""
        return [client.machineIdentifier for client in self.plex_clients]

    @property
    def device_names(self):
        """Return list of devices and aliases names"""
        return self.chromecast_names + self.plex_client_names + self.alias_names

    def update_libraries(self):
        """Update library contents, media titles, & set time updated."""
        from datetime import datetime

        self.plex.reload()
        movies = self.plex.search(libtype="movie", sort="addedAt:desc")
        shows = self.plex.search(libtype="show", sort="addedAt:desc")

        self.lib = {
            "movies": movies,
            "movie_titles": [movie.title for movie in movies],
            "shows": shows,
            "show_titles": [show.title for show in shows],
            "updated": datetime.now(),
        }

    def update_devices(self):
        """Update currently connected cast and client devices."""
        from pychromecast import get_chromecasts

        def cc_callback(chromecast):
            self.chromecasts[chromecast.device.friendly_name] = chromecast

        get_chromecasts(
            blocking=False, callback=cc_callback, zeroconf_instance=self.zconf
        )
        self.plex_clients = self.server.clients()

        if self.remote_server:
            self.update_remote_devices()

    def update_remote_devices(self):
        """Create clients from plex.tv remote endpoint."""
        from plexapi.client import PlexClient

        def setattrs(_self, **kwargs):
            for k, v in kwargs.items():
                setattr(_self, k, v)

        self.resources = None
        remote_client = None

        try:
            self.resources = self.server.myPlexAccount().resources()
        except Exception:
            _LOGGER.warning("Remote endpoint plex.tv not responding. Try again later.")
        if self.resources is None:
            return
        for rc in [r for r in self.resources if r.presence and r.publicAddressMatches]:
            if rc.name not in self.plex_client_names:
                if rc.product == "Plex Media Server":
                    continue
                for connection in [c for c in rc.connections if c.local]:
                    remote_client = PlexClient(
                        server=self.server,
                        baseurl=connection.httpuri,
                        token=self.token,
                    )
                    setattrs(
                        remote_client,
                        machineIdentifier=rc.clientIdentifier,
                        version=rc.productVersion,
                        address=connection.address,
                        product=rc.product,
                        port=connection.port,
                        title=rc.name,
                    )
                    self.plex_clients.append(remote_client)
