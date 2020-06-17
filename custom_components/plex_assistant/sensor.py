"""
Home Assistant component to feed the Upcoming Media Lovelace card with
Plex recently added media.

https://github.com/custom-components/sensor.plex_recently_added

https://github.com/custom-cards/upcoming-media-card

"""
from . import PA
import json
from pychromecast import get_chromecasts
from .helpers import (cc_callback, get_libraries)
from homeassistant.helpers.entity import Entity


def setup_platform(hass, config, add_devices, discovery_info=None):
    name = "Plex Assistant Devices"
    add_devices([PlexAssistantSensor(hass, config, name)], True)


class PlexAssistantSensor(Entity):

    def __init__(self, hass, conf, name):
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def device_state_attributes(self):
        return self._attributes

    async def async_update(self):
        get_chromecasts(blocking=False, callback=cc_callback)
        get_libraries(PA.plex)
        PA.client_names = [client.title for client in PA.server.clients()]
        self._state = str(len(PA.device_names + PA.client_names)
                          ) + ' connected devices.'
        self._attributes = {'device_names': ', '.join(
            PA.device_names + PA.client_names)}
