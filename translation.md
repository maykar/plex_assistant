# Translation

### Contributing to translations

Translations are located in the [localize.py](https://github.com/maykar/plex_assistant/blob/master/custom_components/plex_assistant/localize.py) file.

### How it Works

Translations are held in a dictionary with the language code as the key (in this case "en"):

```
    "en": {
        # Generic Terms
        "play": "play",
        "movie": "movie",
        ...
```

The first grouping of "Generic Terms" are translations of generic words that would be used throughout.
For example the first "play" is the key and should not be changed and the second "play" is the translation of the word.
"on_the" is used to inform us that the user is trying to play the media on a specific device, for example: `play Friends on the Downstairs TV`

```
        # Generic Terms
        "play": "play",
        "movie": "movie",
        "movies": "movies",
        "tv": "tv",
        "show": "show",
        "shows": "shows",
        "on_the": "on the",
```

The next part is an array with the key "play_start". These are phrases of how someone could start the command.
Each of these is tested against some of the generic terms from above to decide if the user is looking for a show or a movie.
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
            "play"
        ],
```

The rest of the dictionary uses keywords, pre, and post.
* "keywords" are the different ways that someone might say what they are looking for.
* "pre" are words that might preceed the keywords.
* "post" are words that might proceed the keywords.

This is done so that the entire phrase can be removed from the command after the options are found, leaving no other words to confuse
the rest of the commands.

For example, the english version for latest episode selection looks like this:
```
        "latest": {
            "keywords": [
                "latest",
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

There is a commented out template at the end of the file that you may copy and paste from.

Please, also consider translating the `README.md` file to a new file with the language code added to the file name. Example: `README_EN.md`
