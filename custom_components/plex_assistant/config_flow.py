from homeassistant import config_entries
from homeassistant.core import callback

import voluptuous as vol

from .const import DOMAIN, HA_VER_SUPPORTED
from .localize import translations


def get_devices(_self):
    devices = []
    for entity in list(_self.hass.data["media_player"].entities):
        info = str(entity.device_info["identifiers"]) if entity.device_info else ""
        if "plex" in info or "cast" in info:
            try:
                devices.append(_self.hass.states.get(entity.entity_id).attributes.get("friendly_name"))
            except AttributeError:
                continue
        else:
            continue
    return devices


def get_servers(_self):
    try:
        return [x.title for x in _self.hass.config_entries.async_entries("plex")]
    except (KeyError, AttributeError):
        return []


def get_schema(_self):
    multi_server_schema = {vol.Optional("server_name"): vol.In(_self.servers)}
    default_schema = {
        vol.Optional("language", default="en"): vol.In(translations.keys()),
        vol.Optional("default_cast"): vol.In(get_devices(_self)),
        vol.Optional("tts_errors", default=True): bool,
    }
    return {**multi_server_schema, **default_schema} if len(_self.servers) > 1 else default_schema


class PlexAssistantFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PlexAssistantOptionsFlowHandler(config_entry)

    def __init__(self):
        self.servers = None

    async def async_step_user(self, user_input=None):
        self.servers = get_servers(self)

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if not HA_VER_SUPPORTED:
            return self.async_abort(reason="ha_ver_unsupported")
        if len(self.servers) < 1:
            return self.async_abort(reason="no_plex_server")
        if user_input is not None:
            server = user_input["server_name"] if "server_name" in user_input else self.servers[0]
            return self.async_create_entry(title=server, data=user_input)

        return await self._show_config_form(user_input)

    async def _show_config_form(self, user_input):
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(get_schema(self)),
        )


class PlexAssistantOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            self.options.update(user_input)
            return await self._update_options()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "start_script",
                        description={"suggested_value": self.options.get("start_script", "")},
                        default="",
                    ): str,
                    vol.Optional(
                        "keyword_replace",
                        description={"suggested_value": self.options.get("keyword_replace", "")},
                        default="",
                    ): str,
                    vol.Required("jump_f", default=self.options.get("jump_f", 30)): int,
                    vol.Required("jump_b", default=self.options.get("jump_b", 15)): int,
                }
            ),
        )

    async def _update_options(self):
        return self.async_create_entry(title="", data=self.options)
