import logging

from homeassistant.const import __version__
from awesomeversion import AwesomeVersion

DOMAIN = "plex_assistant"
HA_VER_SUPPORTED = AwesomeVersion(__version__) >= AwesomeVersion("2021.2.0")
_LOGGER = logging.getLogger(__name__)
