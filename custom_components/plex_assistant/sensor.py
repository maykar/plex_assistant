"""
Companion Sensor for Plex Assistant
https://github.com/maykar/plex_assistant

"""
from homeassistant.helpers.entity import Entity


def setup_platform(hass, config, add_devices, discovery_info=None):
    name = "Plex Assistant Devices"
    add_devices([PlexAssistantSensor(hass, config, name)], True)


class PlexAssistantSensor(Entity):
    def __init__(self, hass, conf, name):
        self._name = name
        self.devices = {}

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def device_state_attributes(self):
        return self._attributes

    def update(self):
        self._state = "No connected devices."
        self._attributes = {
            "Connected Devices": {
                "Cast Devices": "None",
                "Plex Clients": "None",
            }
        }
