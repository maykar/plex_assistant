"""
Companion Sensor for Plex Assistant
https://github.com/maykar/plex_assistant

"""
from . import PA
from homeassistant.helpers.entity import Entity


def setup_platform(hass, config, add_devices, discovery_info=None):
    name = "Plex Assistant Devices"
    add_devices([PlexAssistantSensor(hass, config, name)], True)


class PlexAssistantSensor(Entity):

    def __init__(self, hass, conf, name):
        self._name = name
        self.devices = {}
        self.update_clients = True

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
        clients = [{client.title: {"ID": client.machineIdentifier,
                                   "type": client.product}} for client in PA.clients]
        devicelist = list(PA.devices.keys())
        self._state = str(len(devicelist + clients)) + ' connected devices.'
        self._attributes = {"Connected Devices": {
            'Cast Devices': devicelist or 'None',
            'Plex Clients': clients or 'None'
        }}
