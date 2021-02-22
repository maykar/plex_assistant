# ❱ Plex Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-yellow.svg)](https://github.com/custom-components/hacs) [![hacs_badge](https://img.shields.io/badge/Buy-Me%20a%20Coffee-critical)](https://www.buymeacoffee.com/FgwNR2l)

[Installation](#installation) ｜ [Configuration](#configuration) ｜ [Cast Devices](#cast-devices) ｜ [Commands](#commands)<br>
[Google Assistant Setup](#google-assistant-setup) ｜ [HA Conversation Setup](#home-assistant-conversation-setup) ｜ [Advanced Config](#advanced-configuration)<br><hr>

Plex Assistant is a Home Assistant component to allow Google Assistant, Home Assistant's conversation integration, and more to cast Plex media to Google and Sonos devices, as well as Plex clients. You could use this component with anything that can make a service call to HA as well.

Example: `"Hey Google, tell Plex to play The Walking Dead on the Downstairs TV."`

You can use the component's service (`plex_assistant.command`) to call the commands however you'd like. Visit the services tab in HA's Developer Tools to test it out.

## [Troubleshooting and Issues](https://github.com/maykar/plex_assistant/blob/master/troubleshooting.md)

## Version 1.0.0+

There have been many changes in version 1.0.0, follow the [1.0.0 Update Guide](https://github.com/maykar/plex_assistant/blob/master/ver_one_update.md) if updating from a lower version.

This version requires Home Assistant 2021.2.0+. Use [version 0.3.4](https://github.com/maykar/plex_assistant/releases/tag/0.3.4) if you are on lower versions of HA and find the [old readme here](https://github.com/maykar/plex_assistant/blob/master/OLD_README.md).

## Supporting Development
- :coffee:&nbsp;&nbsp;[Buy me a coffee](https://www.buymeacoffee.com/FgwNR2l)
- :heart:&nbsp;&nbsp;[Sponsor me on GitHub](https://github.com/sponsors/maykar)
- :keyboard:&nbsp;&nbsp;Help with [translation](translation.md), development, or documentation

## Installation
Install by using one of the methods below:

* **Install with [HACS](https://hacs.xyz/):** Search integrations for "Plex Assistant", select it, hit install, and restart.

* **Install Manually:** Install this component by downloading the project and then copying the `/custom_components/plex_assistant/` folder to the `custom_components` folder in your config directory (create the folder if it doesn't exist) and restart.

## Configuration
**You need to have [HA's Plex integration](https://www.home-assistant.io/integrations/plex/) setup in order to use Plex Assistant.**<br>

If you want a Plex Client as your default device, make sure it is open/reachable before setup.

* In your sidebar click "Configuration"
* Go to "Integrations" and click "Add Integration"
* Search for "Plex Assistant" and click it
* Follow the steps shown to select intial config options

Your Plex server is automatically retrieved from Home Assistant's Plex integration, if you have more than one server setup it will ask which one to use.

After setup you can click "Options" on Plex Assistant's card for more config options including: jump forward/back amount and [Advanced Config Options](#advanced-configuration).

## Cast Devices
This component automatically detects compatible media_player entities from Home Assistant (Google Cast devices and Plex Clients). It uses the friendly name from the entities for commands.

## Google Assistant Setup

You can either use IFTTT or DialogFlow to trigger Plex Assistant with Google Assistant.

* IFTTT is the easiest way to set this up, but only if IFTTT supports your language.
* DialogFlow is a bit more involved and has some quirks, like always responding "I'm starting the test version of Plex", but it has support for more languages. Only use DialogFlow if your language is otherwise unsupported.

<details>
  <summary><b>IFTTT Setup Guide</b></summary>
  
## IFTTT Setup

#### In Home Assistant

* Go to "Configuration" in your HA sidebar and select "Integrations"
* Hit the add button and search for "IFTTT" and click configure.
* Follow the on screen instructions.
* Copy or save the URL that is displayed at the end, we'll need it later.
* Click "Finish"

#### In IFTTT

Visit [ifttt.com](https://ifttt.com/) and sign up or sign in.

* Create a new applet
* Click "Add" next to "If This".
* Search for and select "Google Assistant"
* Select "Say phrase with text ingredient"

Now you can select how you want to trigger this service, you can select up to 3 ways to invoke it. I use things like `tell plex to $` or `have plex $`. The dollar sign will be the phrase sent to this component. You can also set a response from the Google Assistant if you'd like. Select your language (as long as it's supported, see list above), then hit "Create Trigger" to continue.

* Click "Add" next to "Then That"
* Search for and select "Webhooks", then select "Make a web request"
* In the URL field enter the webhook URL HA provided you earlier
* Select method "Post" and content type "application/json"
* Then copy and paste the code below into the body field

`{ "action": "call_service", "service": "plex_assistant.command", "command": "{{TextField}}" }`

Finally click "Create Action", then "Continue", and then "Finish".

You can now trigger Plex Assistant by saying "Hey Google, tell plex to..." or "Hey Google, ask plex to..."

</details>

<details>
  <summary><b>DialogFlow Setup Guide</b></summary>

## DialogFlow Setup

#### In Home Assistant

The DialogFlow trigger requires Home Assistant's [Conversation integration](https://www.home-assistant.io/integrations/conversation/) to be enabled.

* Go to "Configuration" in your HA sidebar and select "Integrations"
* Hit the add button and search for "Dialogflow".
* Copy or save the URL that is displayed, we'll need it later.
* Click "Finish"

#### In DialogFlow

Download [Plex_Assistant_DialogFlow.zip](https://github.com/maykar/plex_assistant/raw/master/Plex_Assistant_DialogFlow.zip) and then visit https://dialogflow.cloud.google.com . Sign up or sign in using the same Google account tied to your Google Assistant. Keep going until you get to the "Welcome to Dialogflow!" page with "Create Agent" in the sidebar.

* Click on Create Agent and Type "Plex" as the agent name and hit "Create"
* Now click the settings icon next to "Plex" in the sidebar
* Navigate to "Export and Import" and click "Restore from ZIP"
* Select the `Plex_Assistant_DialogFlow.zip` file we downloaded earlier and restore
* Click "Fulfillment" in the sidebar and change the URL to the one HA gave us for DialogFlow
* Scroll down and hit "Save"

If you will be using English as your language you can ignore the next group of steps.

* To add your language click the plus sign in the sidebar next to "en"
* Select your language under "English - en" and hit "Save" in the top right
* Click your language code next to "en" in the sidebar
* Click "Intents" in the sidebar and then click the "Plex" intent
* In the "Training phrases" section type "command"
* Double click on the word "command" that you just entered and select "@sys.any:command"
* Hit "Save" in the top right.

If you would like to add a response for the assistant to say after your command:

* Click "Intents" in the sidebar and then click the "Plex" intent
* In "Responses" write the desired result under "Text Response"
* Hit "Save" in the top right.

You can now trigger Plex Assistant by saying "Hey Google, tell plex to..." or "Hey Google, ask plex to..."

</details>

### Currently Supported Languages:
| Language |  Code  |        IFTTT         |         DialogFlow         |       Music Support        |
|:---------|:------:|:--------------------:|:--------------------------:|:--------------------------:|
|<img src='https://raw.githubusercontent.com/yammadev/flag-icons/master/png/DK%402x.png?raw=true' height='12'>&nbsp;&nbsp;&nbsp;**Danish**|`"da"`|:x:|:heavy_check_mark:|:x:|
|<img src='https://raw.githubusercontent.com/yammadev/flag-icons/master/png/NL%402x.png?raw=true' height='12'>&nbsp;&nbsp;&nbsp;**Dutch**|`"nl"`|:x:|:heavy_check_mark:|:x:|
|<img src='https://raw.githubusercontent.com/yammadev/flag-icons/master/png/GB%402x.png?raw=true' height='12'>&nbsp;&nbsp;&nbsp;**English**|`"en"`|:heavy_check_mark:|:heavy_check_mark:|:heavy_check_mark:|
|<img src='https://raw.githubusercontent.com/yammadev/flag-icons/master/png/ES%402x.png?raw=true' height='12'>&nbsp;&nbsp;&nbsp;**Spanish**|`"es"`|:heavy_check_mark:|:heavy_check_mark:|:x:|
|<img src='https://raw.githubusercontent.com/yammadev/flag-icons/master/png/FR%402x.png?raw=true' height='12'>&nbsp;&nbsp;&nbsp;**French**|`"fr"`|:heavy_check_mark:|:heavy_check_mark:|:x:|
|<img src='https://raw.githubusercontent.com/yammadev/flag-icons/master/png/DE%402x.png?raw=true' height='12'>&nbsp;&nbsp;&nbsp;**German**|`"de"`|:heavy_check_mark:|:heavy_check_mark:|:x:|
|<img src='https://raw.githubusercontent.com/yammadev/flag-icons/master/png/IT%402x.png?raw=true' height='12'>&nbsp;&nbsp;&nbsp;**Italian**|`"it"`|:heavy_check_mark:|:heavy_check_mark:|:x:|
|<img src='https://raw.githubusercontent.com/yammadev/flag-icons/master/png/NO%402x.png?raw=true' height='12'>&nbsp;&nbsp;&nbsp;**Norwegian**|`"nb"`|:x:|:heavy_check_mark:|:x:|
|<img src='https://raw.githubusercontent.com/yammadev/flag-icons/master/png/PT%402x.png?raw=true' height='12'>&nbsp;&nbsp;&nbsp;**Portuguese**|`"pt"`|:x:|:heavy_check_mark:|:heavy_check_mark:|
|<img src='https://raw.githubusercontent.com/yammadev/flag-icons/master/png/SV%402x.png?raw=true' height='12'>&nbsp;&nbsp;&nbsp;**Swedish**|`"sv"`|:x:|:heavy_check_mark:|:x:|

#### [Help add or improve support for more languages.](translation.md)<hr>

## Home Assistant Conversation Setup

Requires Home Assistant's [Conversation integration](https://www.home-assistant.io/integrations/conversation/) to be enabled.

By default Plex Assistant will work with HA's Conversation integration with the phrases `"Tell Plex to {command}"` and `"{command} with Plex"` with no additional configuration nessisary. All the languages in the table above are supported, but you'd need to make a trigger phrase in your language. If you would like to add more trigger phrases you can do so by using the code below as an example.

```yaml
conversation:
  intents:
    Plex:
     - "Plex please would you {command}"
     - "I command plex to {command}"
```

## Commands

#### Fuzzy Matching
A show or movie's title and the device used in your phrase are processed using a fuzzy search. Meaning it will select the closest match using your Plex media titles and available cast device names. `"play walk in deed on the dawn tee"` would become `"Play The Walking Dead on the Downstairs TV."`. This even works for partial matches. `play Pets 2` will match `The Secret Life of Pets 2`.

If no season/episode is specified for a TV show Plex Assistant will play the first unwatched or first in progress episode by default.

#### You can say things like:
* `"play the latest episode of Breaking Bad on the Living Room TV"`
* `"play Breaking Bad"`
* `"play Add it Up by the Violent Femmes"`
* `"play the track Time to Pretend"`
* `"play the album Time to Pretend by MGMT"`
* `"play ondeck"`
* `"play random unwatched TV"`
* `"play season 1 episode 3 of The Simpsons"`
* `"play the first season second episode of Taskmaster on the Theater System"`

### Filter Keywords:
* `season, episode, movie, show`
* `artist, album, track, playlist`
* `latest, recent, new`
* `unwatched, next`
* `ondeck`
* `random, shuffle, randomized, shuffled`

Filter keywords can be combined. For example `"play random unwatched movies"` will start playing a list of all unwatched movies in random order.

### Control Commands:
* `play`
* `pause`
* `stop`
* `next, skip, next track, skip forward`
* `previous, back, go back`
* `jump forward, fast forward, forward`
* `jump back, rewind`

Be sure to add the name of the device to control commands if it is not the default device. `"stop downstairs tv"` or `"previous on the livingroom tv"`.

If no cast device is specified in your command, the default device set in your config is used. A cast device will only be found if at the end of the command and when preceded with the word `"on"` or words `"on the"`. Example: *"play friends **ON** downstairs tv"*

Control commands are the only ones that don't require the `"on"` or `"on the"` before the device name.

I've tried to take into account many different ways that commands could be phrased. If you find a phrase that isn't working and you feel should be implemented, please make an issue or give the keyword replacement option a try (see below).

## Advanced Configuration

There are two advanced configuration options: keyword replacements and start scripts. HA's UI configuration doesn't have a good way to impliment these kinds of options yet, so formatting is very important for these options. Once there is a better way to handle these I will update the UI.

## Keyword Replacements

This option could be used for a few different purposes. The formatting is the word/phrase you want to say in quotes followed by a colon and then the word/phrase you want replace it with in quotes. Seperate multiple replacements with a comma.

Here's an example to add to the commands "next" and "previous" with alternatives:
```
"full speed ahead":"next", "reverse full power":"previous"
```
Using this config would allow you to say "full speed ahead" to go to the next track and "reverse full power" to go to the previous. You can still use the default commands as well.

Another use example would be if you have multiple Star Trek series, but want a specific one to play when you just say "Star Trek":
```
"star trek":"star trek the next generation"
```

And yet another use would be to improve translations, for example: If there are feminine and masculine variations for your language you can now add those variations.

## Start Scripts

This option will trigger a script to start a Plex client if it is currently unavailable. For example: You have a Roku with the Plex app, but need it to be open for Plex Assistant to control it.<br><br>The formatting needed is the friendly name of the client that you want to open in quotes (case sensitive) followed by a colon then the HA script to start the client in quotes. Seperate multiple entries with a comma.
```
"LivingRoom TV":"script.start_lr_plex", "Bedroom TV":"script.open_br_plex"
```
The script would be different for every device and some devices might not have the ability to do this.<br>
Plex Assistant will wait for the start script to finish before continuing, so having a check for device availability is advisable. That way the script can both wait for the device to be available or quickly end if it already is.<br><br>
The example below would start the Plex app on a Roku device.<br>The script waits until the app is open on the device and the app reports as available (take note of the comments in the code). 

```
roku_plex:
  sequence:
    - choose:
        #### If Plex is already open on the device, do nothing
        - conditions:
            - condition: template
              value_template: >-
                {{ state_attr('media_player.roku','source') == 'Plex - Stream for Free' }}
          sequence: []
      default:
      #### If Plex isn't open on the device, open it
      #### You could even add a service to turn your TV on here
      - service: media_player.select_source
        entity_id: 'media_player.roku'
        data:
          source: 'Plex - Stream for Free'
      - repeat:
          #### Wait until the Plex App/Client is available
          while:
            - condition: template
              #### Loop until Plex App or client report as available and stop after 20 tries
              value_template: >-
                {{ (state_attr('media_player.roku','source') != 'Plex - Stream for Free' or
                   is_state('media_player.plex_plex_for_roku_roku', 'unavailable')) and
                   repeat.index <= 20 }}
          sequence:
            #### Scan to update device status
            - service: plex.scan_for_clients
            - delay:
                seconds: 1
      #### Optional delay after device is found. Uncomment the 2 lines for delay below
      #### if your device needs a few seconds to respond to commands. Increase delay as needed.
      # - delay:
      #     seconds: 3
  mode: single
```
