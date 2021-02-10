# Translation

### Contributing to translations

Translations are located in the [localize.py](https://github.com/maykar/plex_assistant/blob/master/custom_components/plex_assistant/localize.py) file.

Translations are held in a dictionary with the language code as the key (in this case "en"):

```
    "en": {
        # Generic Terms
        "play": "play",
        ...
```

### Generic Terms

The first grouping of "Generic Terms" are translations of generic words that would be used throughout.
For example in `"play": "play"` the first "play" is the key and should not be changed and the second "play" is the translation of the word.

The keys "movies" and "shows" contain a list of keywords that would inform us of the media type the user is looking for.

```
        # Generic Terms
        "play": "play",
        "movies": [
            "movie",
            "film",
        ],
        "shows": [
            "episode",
            "tv",
            "show"
        ],
```

### Controls

These are the media player controls.

```
        "controls": {
            "play": "play",
            "pause": "pause",
            "stop": "stop",
            "jump_forward": "jump forward",
            "jump_back": "jump back",
        },
```

### Errors

Text for errors.

```
        "not_found": "not found",
        "cast_device": "cast device",
        "no_call": "No command was received.",
```

### Invoke Commands

The next part is an array with the key "play_start". These are phrases of how someone could start the command.
Each of these is tested against "movies" and "shows" from above to decide if the user is looking for a show or a movie.
Once any of the play_start phrases are found they are removed from the command so that they don't add to other options like
the media title, so it is important to have as many ways that it could be phrased included.
```
        # Invoke Command
        "play_start": [
            "play the movie",
            "play movie",
            "play the tv show",
            "play tv show",
            "play the show",
            "play tv",
            "play show",
            "play the",
            "play"
        ],
```

### Keywords, Pre, and Post

The rest of the dictionary uses keywords, pre, and post.
* "keywords" are the different ways that someone might say what they are looking for.
* "pre" are words that might preceed the keywords.
* "post" are words that might proceed the keywords.

Pre and post should be ordered by proximity to the keyword. For for the example with a keyword "latest" and a command of `"play the very latest episode of"` the pre list should be in this order `"very", "the"` and the post list should be in this order `"episode", "of"` (the word "very" isn't actually handled, but just used as an example).

For example, the english version for latest episode selection looks like this:
```
        "latest": {
            "keywords": [
                "latest",
                "recent",
                "new",
            ],
            "pre": [
                "the",
            ],
            "post": [
                "episode",
                "of",
            ],
        },
```
This will allow the user to say something like `play the latest episode of Friends`, `play latest of Friends`, `play latest Friends`, or `play the latest Friends`
and the options for latest and media type are set, then our command in each case becomes `play Friends`.


### Ordinal Numbers

The ordinals section is for converting ordinal numbers (`first, second, third...`) into their corrisponding integers (`1, 2, 3...`). I'm not entirely sure how other languages handle ordinals, but this is the only section where you would edit the keys for translation and leave the integers alone. This section also includes "pre" and "post" as above, do not change their keys.

```
        # Ordinal Numbers to Integers
        "ordinals": {
            "first": "1",
            "second": "2",
            "third": "3",
            "fourth": "4",
            "fifth": "5",
            "sixth": "6",
            "seventh": "7",
            "eighth": "8",
            "ninth": "9",
            "tenth": "10",
            "pre": [
                "the",
            ],
            "post": [],
        },
```

Ordinal numbers between 1 and 10 (first and tenth) are often represented as words by Google Assistant, but anything past that is returned as an integer followed by "st", "nd", "rd" or "th" (`31st, 42nd, 23rd, 11th`). The way we would handle those in english would be using the "pre" key like in the "episode" example below.

```
        "episode": {
            "keywords": [
                "episode",
            ],
            "pre": [
                'st',
                'nd',
                'rd',
                'th',
            ],
            "post": [
                "number",
                "of",
            ],
        },
```

### Seperator

This is the word that seperates the media from cast device. In English it is "on". It operates like the keywords above with a post and pre, but may only contain one keyword:

```
        "separator": {
            # Only use one keyword for this one.
            "keywords": [
                "on",
            ],
            "pre": [],
            "post": [
                "the",
            ],
        },
```

### Additional Info

There is a commented out template at the end of the file that you may copy and paste from.

Please, also consider translating the `README.md` file and `translations/en.json` to a new file with the language code added to the file name. Example: `README_NL.md` and `nl.json`.
