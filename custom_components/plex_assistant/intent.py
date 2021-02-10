import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import intent

from .const import DOMAIN


async def async_setup_intents(hass):
    intent.async_register(hass, PlexAssistantIntent())
    hass.components.conversation.async_register(
        "Plex",
        ["Tell Plex to {command}", "{command} with Plex"],
    )


class PlexAssistantIntent(intent.IntentHandler):
    intent_type = "Plex"
    slot_schema = {"command": cv.string}

    async def async_handle(self, intent_obj):
        slots = self.async_validate_slots(intent_obj.slots)
        if "initialize_plex_intent" in slots["command"]["value"]:
            return
        await intent_obj.hass.services.async_call(DOMAIN, "command", {"command": slots["command"]["value"]})
        response = intent_obj.create_response()
        response.async_set_speech("Sending command to Plex.")
        return response
