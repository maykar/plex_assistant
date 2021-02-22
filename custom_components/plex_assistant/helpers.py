import re
import time
import uuid
import json
import pychromecast

from fuzzywuzzy import fuzz
from fuzzywuzzy import process as fw
from datetime import timedelta
from gtts import gTTS
from homeassistant.components.plex.services import get_plex_server
from homeassistant.core import Context
from pychromecast.controllers.plex import PlexController

from .const import DOMAIN, _LOGGER


def fuzzy(media, lib, scorer=fuzz.QRatio):
    if isinstance(lib, list) and len(lib) > 0:
        return fw.extractOne(media, lib, scorer=scorer)
    return ["", 0]


def process_config_item(options, item_type):
    item = options.get(item_type)
    if item:
        try:
            item = json.loads("{" + item + "}")
            for i in item.keys():
                _LOGGER.debug(f"{item_type} {i}: {item[i]}")
        except:
            item = {}
        return item
    else:
        return {}


async def get_server(hass, config, server_name):
    try:
        await hass.helpers.discovery.async_discover(None, None, "plex", config)
        return get_plex_server(hass, server_name)._plex_server
    except Exception as ex:
        if ex.args[0] == "No Plex servers available":
            server_name_str = ", the server_name is correct," if server_name else ""
            _LOGGER.warning(
                f"Plex Assistant: Plex server not found. Ensure that you've setup the HA Plex integration{server_name_str} and the server is reachable."
            )
        else:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            _LOGGER.warning(message)


def get_devices(hass, pa):
    for entity in list(hass.data["media_player"].entities):
        info = str(entity.device_info.get("identifiers", "")) if entity.device_info else ""
        dev_type = [x for x in ["cast", "sonos", "plex", ""] if x in info][0]
        if not dev_type:
            continue
        try:
            name = hass.states.get(entity.entity_id).attributes.get("friendly_name")
        except:
            continue
        pa.devices[name] = {"entity_id": entity.entity_id, "device_type": dev_type}


def device_responding(hass, pa, device):
    responding = hass.services.call(
                    "media_player",
                    "media_play",
                    {"entity_id": pa.devices[device]["entity_id"]},
                    blocking=True,
                    limit=30
                 )
    return responding


def run_start_script(hass, pa, command, start_script, device):
    if device[0] in start_script.keys():
        start = hass.data["script"].get_entity(start_script[device[0]])
        start.script.run(context=Context())
        get_devices(hass, pa)
        return fuzzy(command["device"] or default_device, list(pa.devices.keys()))
    return device


async def listeners(hass):
    def ifttt_webhook_callback(event):
        if event.data["service"] == "plex_assistant.command":
            _LOGGER.debug("IFTTT Call: %s", event.data["command"])
            hass.services.call(DOMAIN, "command", {"command": event.data["command"]})

    listener = hass.bus.async_listen("ifttt_webhook_received", ifttt_webhook_callback)

    try:
        await hass.services.async_call("conversation", "process", {"text": "tell plex to initialize_plex_intent"})
    except:
        pass

    return listener


def media_service(hass, entity_id, call, payload=None):
    args = {"entity_id": entity_id}
    if call == "play_media":
        args = {**args, **{"media_content_type": "video", "media_content_id": payload}}
    elif call == "media_seek":
        args = {**args, **{"seek_position": payload}}
    hass.services.call("media_player", call, args)


def jump(hass, device, amount):
    if device["device_type"] == "plex":
        media_service(hass, device["entity_id"], "media_pause")
        time.sleep(0.5)

    offset = hass.states.get(device["entity_id"]).attributes.get("media_position", 0) + amount
    media_service(hass, device["entity_id"], "media_seek", offset)

    if device["device_type"] == "plex":
        media_service(hass, device["entity_id"], "media_play")


def cast_next_prev(hass, zeroconf, plex_c, device, direction):
    entity = hass.data["media_player"].get_entity(device["entity_id"])
    cast, browser = pychromecast.get_listed_chromecasts(uuids=[uuid.UUID(entity._cast_info.uuid)], zeroconf_instance=zeroconf)
    pychromecast.discovery.stop_discovery(browser)
    cast[0].register_handler(plex_c)
    cast[0].wait()
    if direction == "next":
        plex_c.next()
    else:
        plex_c.previous()


def remote_control(hass, zeroconf, control, device):
    plex_c = PlexController()

    if control == "jump_forward":
        jump(hass, device, jump_amount[0])
    elif control == "jump_back":
        jump(hass, device, -jump_amount[1])
    elif control == "next_track" and device["device_type"] == "cast":
        cast_next_prev(hass, zeroconf, plex_c, device, "next")
    elif control == "previous_track" and device["device_type"] == "cast":
        cast_next_prev(hass, zeroconf, plex_c, device, "previous")
    else:
        media_service(hass, device["entity_id"], f"media_{control}")


def seek_to_offset(hass, offset, entity):
    if offset > 0:
        timeout = 0
        while not hass.states.is_state(entity, "playing") and timeout < 100:
            time.sleep(0.10)
            timeout += 1

        timeout = 0
        if hass.states.is_state(entity, "playing"):
            media_service(hass, entity, "media_pause")
            while not hass.states.is_state(entity, "paused") and timeout < 100:
                time.sleep(0.10)
                timeout += 1

        if hass.states.is_state(entity, "paused"):
            if hass.states.get(entity).attributes.get("media_position", 0) < 9:
                media_service(hass, entity, "media_seek", offset)
            media_service(hass, entity, "media_play")


def no_device_error(localize, device=None):
    device = f': "{device.title()}".' if device else "."
    _LOGGER.warning(
        "{0} {1}{2}".format(
            localize["cast_device"].capitalize(),
            localize["not_found"],
            device,
        )
    )


def media_error(command, localize):
    error = ""
    for keyword in ["latest", "unwatched", "ondeck"]:
        if command[keyword]:
            error += localize[keyword]["keywords"][0] + " "
    if command["media"]:
        error += "%s " % str(command["media"]).capitalize()
    for keyword in ["season", "episode"]:
        if command[keyword]:
            error += "%s %s " % (localize[keyword]["keywords"][0], command[keyword])
    error += localize["not_found"] + "."
    return error.capitalize()


def play_tts_error(hass, tts_dir, device, error, lang):
    tts = gTTS(error, lang=lang)
    tts.save(tts_dir + "error.mp3")
    hass.services.call(
        "media_player",
        "play_media",
        {
            "entity_id": device,
            "media_content_type": "audio/mp3",
            "media_content_id": "/local/plex_assist_tts/error.mp3",
        },
    )


def get_title(item, deep=False):
    if item.type == "movie":
        return item.title
    elif getattr(item, "show", None):
        return item.show().title if deep else item.title
    return None


def filter_media(pa, option, media, lib):
    if getattr(media, "type", None) in ["artist", "album", "track"]:
        return media
    elif media and lib:
        media = next(m for m in lib if m.title == media)
    elif lib:
        media = lib

    if option["season"] and option["episode"]:
        return media.episode(season=int(option["season"]), episode=int(option["episode"]))

    if option["season"]:
        media = media.season(title=int(option["season"]))

    if option["ondeck"]:
        if option["media"]:
            ondeck = pa.library.onDeck()
            media = list(
                filter(
                    lambda x: (get_title(x) == media.title)
                    or (get_title(media) == x.show().title)
                    or (get_title(media, True) == x.show().title),
                    ondeck,
                )
            )
        elif option["library"]:
            media = pa.library.sectionByID(option["library"][0].librarySectionID).onDeck()
        else:
            media = pa.library.onDeck()
    if option["unwatched"]:
        if not media and not lib:
            media = list(filter(lambda x: not x.isWatched, pa.library.recentlyAdded()))
        elif isinstance(media, list):
            media = list(filter(lambda x: not x.isWatched, media))
        elif getattr(media, "unwatched", None):
            media = media.unwatched()
    if option["latest"]:
        if not option["unwatched"]:
            if not media:
                if not lib:
                    tv_id = pa.media["shows"][0].librarySectionID
                    movie_id = pa.media["movies"][0].librarySectionID
                    media = (
                        pa.library.sectionByID(tv_id).recentlyAdded() + pa.library.sectionByID(movie_id).recentlyAdded()
                    )
                    media.sort(key=lambda x: getattr(x, "addedAt", None), reverse=True)
                else:
                    media = pa.library.sectionByID(option["library"][0].librarySectionID).recentlyAdded()
        else:
            if getattr(media, "type", None) in ["show", "season"]:
                media = media.episodes()[-1]
            elif isinstance(media, list):
                media.sort(key=lambda x: getattr(x, "addedAt", None), reverse=True)
    if getattr(media, "TYPE", None) == "show":
        unwatched = media.unwatched()
        return unwatched if unwatched and not option["random"] else media.episodes()
    return media


def roman_numeral_test(media, lib):
    regex = re.compile(r"\b(\d|(10))\b")
    replacements = {
        "1": "I",
        "2": "II",
        "3": "III",
        "4": "IV",
        "5": "V",
        "6": "VI",
        "7": "VII",
        "8": "VIII",
        "9": "IX",
        "10": "X",
    }

    if len(re.findall(regex, media)) > 0:
        replaced = re.sub(regex, lambda m: replacements[m.group(1)], media)
        return fuzzy(replaced, lib, fuzz.WRatio)
    return ["", 0]


def find_media(selected, media, lib):
    result = ""
    library = ""
    if getattr(media, "type", None) in ["artist", "album", "track"]:
        return [media, lib[f"{media.type}s"]]
    elif selected["library"]:
        library = selected["library"]
        section = f"{library[0].type}_titles"
        if media:
            result = fuzzy(media, lib[section], fuzz.WRatio)
            roman_test = roman_numeral_test(media, lib[section])
            result = result[0] if result[1] > roman_test[1] else roman_test[0]
    elif media:
        item = {}
        score = {}
        for category in ["show", "movie", "artist", "album", "track"]:
            lib_titles = lib[f"{category}_titles"]
            standard = fuzzy(media, lib_titles, fuzz.WRatio) if lib_titles else ["", 0]
            roman = roman_numeral_test(media, lib_titles) if lib_titles else ["", 0]

            winner = standard if standard[1] > roman[1] else roman
            item[category] = winner[0]
            score[category] = winner[1]

        winning_category = max(score, key=score.get)
        result = item[winning_category]
        library = lib[f"{winning_category}s"]

    return [result, library]
