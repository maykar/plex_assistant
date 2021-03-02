import re
import time
import uuid
import pychromecast

from rapidfuzz import fuzz, process
from gtts import gTTS
from json import JSONDecodeError, loads
from homeassistant.components.plex.services import get_plex_server
from homeassistant.exceptions import HomeAssistantError, ServiceNotFound
from homeassistant.core import Context
from pychromecast.controllers.plex import PlexController

from .const import DOMAIN, _LOGGER


def fuzzy(media, lib, scorer=fuzz.QRatio):
    if isinstance(lib, list) and len(lib) > 0:
        return process.extractOne(media, lib, scorer=scorer) or ["", 0]
    return ["", 0]


def process_config_item(options, option_type):
    option = options.get(option_type)
    if not option:
        return {}
    try:
        option = loads("{" + option + "}")
        for i in option.keys():
            _LOGGER.debug(f"{option_type} {i}: {option[i]}")
    except (TypeError, AttributeError, KeyError, JSONDecodeError):
        _LOGGER.warning(f"There is a formatting error in the {option_type.replace('_', ' ')} config.")
        option = {}
    return option


async def get_server(hass, config, server_name):
    try:
        await hass.helpers.discovery.async_discover(None, None, "plex", config)
        return get_plex_server(hass, server_name)._plex_server
    except HomeAssistantError as error:
        server_name_str = ", the server_name is correct," if server_name else ""
        _LOGGER.warning(
            f"Plex Assistant: {error.args[0]}. Ensure that you've setup the HA "
            f"Plex integration{server_name_str} and the server is reachable. "
        )


def get_devices(hass, pa):
    for entity in list(hass.data["media_player"].entities):
        info = str(entity.device_info.get("identifiers", "")) if entity.device_info else ""
        dev_type = [x for x in ["cast", "sonos", "plex", ""] if x in info][0]
        if not dev_type:
            continue
        try:
            name = hass.states.get(entity.entity_id).attributes.get("friendly_name")
        except AttributeError:
            continue
        pa.devices[name] = {"entity_id": entity.entity_id, "device_type": dev_type}


def run_start_script(hass, pa, command, start_script, device, default_device):
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
    except ServiceNotFound:
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
    cast, browser = pychromecast.get_listed_chromecasts(
        uuids=[uuid.UUID(entity._cast_info.uuid)], zeroconf_instance=zeroconf
    )
    pychromecast.discovery.stop_discovery(browser)
    cast[0].register_handler(plex_c)
    cast[0].wait()
    if direction == "next":
        plex_c.next()
    else:
        plex_c.previous()


def remote_control(hass, zeroconf, control, device, jump_amount):
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
    if offset < 1:
        return
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
    _LOGGER.warning(f"{localize['cast_device'].capitalize()} {localize['not_found']}{device}")


def media_error(command, localize):
    error = "".join(
        f"{localize[keyword]['keywords'][0]} " for keyword in ["latest", "unwatched", "ondeck"] if command[keyword]
    )
    if command["media"]:
        media = command["media"]
        media = media if isinstance(media, str) else getattr(media, "title", str(media))
        error += f"{media.capitalize()} "
    elif command["library"]:
        error += f"{localize[command['library']+'s'][0]} "
    for keyword in ["season", "episode"]:
        if command[keyword]:
            error += f"{localize[keyword]['keywords'][0]} {command[keyword]} "
    error += f"{localize['not_found']}."
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


def filter_media(pa, command, media, library):
    offset = 0

    if library == "playlist":
        media = pa.server.playlist(media) if media else pa.server.playlists()
    elif media or library:
        media = pa.library.search(title=media or None, libtype=library or None)

    if isinstance(media, list) and len(media) == 1:
        media = media[0]

    if command["episode"]:
        media = media.episode(season=int(command["season"] or 1), episode=int(command["episode"]))
    elif command["season"]:
        media = media.season(season=int(command["season"]))

    if command["ondeck"]:
        title, libtype = [command["media"], command["library"]]
        if getattr(media, "onDeck", None):
            media = media.onDeck()
        elif title or libtype:
            search_result = pa.library.search(title=title or None, libtype=libtype or None, limit=1)[0]
            if getattr(search_result, "onDeck", None):
                media = search_result.onDeck()
            else:
                media = pa.library.sectionByID(search_result.librarySectionID).onDeck()
        else:
            media = pa.library.sectionByID(pa.tv_id).onDeck() + pa.library.sectionByID(pa.movie_id).onDeck()
            media.sort(key=lambda x: getattr(x, "addedAt", None), reverse=False)

    if command["unwatched"]:
        if isinstance(media, list) or (not media and not library):
            media = media[:200] if isinstance(media, list) else pa.library.recentlyAdded()
            media = [x for x in media if getattr(x, "viewCount", 0) == 0]
        elif getattr(media, "unwatched", None):
            media = media.unwatched()[:200]

    if command["latest"] and not command["unwatched"]:
        if library and not media and pa.section_id[library]:
            media = pa.library.sectionByID(pa.section_id[library]).recentlyAdded()[:200]
        elif not media:
            media = pa.library.sectionByID(pa.tv_id).recentlyAdded()
            media += pa.library.sectionByID(pa.mov_id).recentlyAdded()
            media.sort(key=lambda x: getattr(x, "addedAt", None), reverse=True)
            media = media[:200]
    elif command["latest"]:
        if getattr(media, "type", None) in ["show", "season"]:
            media = media.episodes()[-1]
        elif isinstance(media, list):
            media = media[:200]
            media.sort(key=lambda x: getattr(x, "addedAt", None), reverse=True)

    if not command["random"] and media:
        pos = getattr(media[0], "viewOffset", 0) if isinstance(media, list) else getattr(media, "viewOffset", 0)
        offset = (pos / 1000) - 5 if pos > 15 else 0

    if getattr(media, "TYPE", None) == "show":
        unwatched = media.unwatched()[:30]
        media = unwatched if unwatched and not command["random"] else media.episodes()[:30]
    elif getattr(media, "TYPE", None) == "episode":
        episodes = media.show().episodes()
        episodes = episodes[episodes.index(media) : episodes.index(media) + 30]
        media = pa.server.createPlayQueue(episodes, shuffle=int(command["random"]))
    elif getattr(media, "TYPE", None) in ["artist", "album"]:
        tracks = media.tracks()
        media = pa.server.createPlayQueue(tracks, shuffle=int(command["random"]))
    elif getattr(media, "TYPE", None) == "track":
        tracks = media.album().tracks()
        tracks = tracks[tracks.index(media) :]
        media = pa.server.createPlayQueue(tracks, shuffle=int(command["random"]))

    if getattr(media, "TYPE", None) != "playqueue" and media:
        media = pa.server.createPlayQueue(media, shuffle=int(command["random"]))

    return [media, 0 if media and media.items[0].listType == "audio" else offset]


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


def find_media(pa, command):
    result = ""
    lib = ""
    if getattr(command["media"], "type", None) in ["artist", "album", "track"]:
        return [command["media"], command["media"].type]
    if command["library"]:
        lib_titles = pa.media[f"{command['library']}_titles"]
        if command["media"]:
            result = fuzzy(command["media"], lib_titles, fuzz.WRatio)
            roman_test = roman_numeral_test(command["media"], lib_titles)
            result = result[0] if result[1] > roman_test[1] else roman_test[0]
    elif command["media"]:
        item = {}
        score = {}
        for category in ["show", "movie", "artist", "album", "track", "playlist"]:
            lib_titles = pa.media[f"{category}_titles"]
            standard = fuzzy(command["media"], lib_titles, fuzz.WRatio) if lib_titles else ["", 0]
            roman = roman_numeral_test(command["media"], lib_titles) if lib_titles else ["", 0]

            winner = standard if standard[1] > roman[1] else roman
            item[category] = winner[0]
            score[category] = winner[1]

        winning_category = max(score, key=score.get)
        result = item[winning_category]
        lib = winning_category

    return [result, lib or command["library"]]
