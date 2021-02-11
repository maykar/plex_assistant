import logging

from homeassistant.const import __version__ as HAVERSION
from awesomeversion import AwesomeVersion

DOMAIN = "plex_assistant"
MINIMUM_HA_VERSION = "2021.2.0"
HA_VER_SUPPORTED = AwesomeVersion(HAVERSION) >= AwesomeVersion(MINIMUM_HA_VERSION)
_LOGGER = logging.getLogger(__name__)
