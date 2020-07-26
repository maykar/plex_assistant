# ❱ Plex Assistant

[Installation](#installation) ｜ [Configuration](#configuration) ｜ [IFTTT/DialogFlow Setup](#iftttdialogflow-setup) ｜ [Commands](#commands) ｜ [Help Translate](#translation)<br><hr>

Plex Assistant is a Home Assistant component to allow Google Assistant to cast Plex media to Google devices and Plex clients with a bit of help from IFTTT or DialogFlow. You could use this component with anything that can make a service call to HA as well (see the IFTTT and DialogFlow automations below as a starting point).

Example: `"Hey Google, tell Plex to play The Walking Dead on the Downstairs TV."`

You can use the component's service without IFTTT/DialogFlow to call the commands however you'd like. Visit the services tab in HA's Developer Tools to test it out.

## Supporting Development
- :coffee:&nbsp;&nbsp;[Buy me a coffee](https://www.buymeacoffee.com/FgwNR2l)
- :1st_place_medal:&nbsp;&nbsp;[Tip some Crypto](https://github.com/sponsors/maykar)
- :heart:&nbsp;&nbsp;[Sponsor me on GitHub](https://github.com/sponsors/maykar)
- :keyboard:&nbsp;&nbsp;Help with translation, development, or documentation
  <br><br>

## Author's note
This is just a side project made to fill the absence of native Google Assistant support in Plex and the fact that the Phlex/FlexTV projects aren’t in working order at the moment.

This project is not a priority of mine as Plex could add Google Assistant support or FlexTV may become viable again at any time. That being said, I will try to add features and fix issues until that time. As always, I both welcome and greatly appreciate pull requests.

Thank you for understanding.

## Installation
Install by using one of the methods below:

* **Install with [HACS](https://hacs.xyz/):** Search integrations for "Plex Assistant", select and hit install. Add the configuration (see below) to your configuration.yaml file.

* **Install Manually:** Install this component by copying all of [these files](https://github.com/maykar/plex_assistant/tree/master/custom_components/plex_assistant) to `/custom_components/plex_assistant/`. Add the configuration (see below) to your configuration.yaml file.

## Configuration
Add config to your configuration.yaml file.

| Key          | Default | Necessity    | Description
| :--          | :------ | :--------    | :----------
| url          |         | **Required** | The full url to your Plex instance including port.
| token        |         | **Required** | Your Plex token. [How to find your Plex token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/).
| default_cast |         | Optional     | The name of the cast device to use if none is specified.
| language     | 'en'    | Optional     | Language code. See Below for supported Languages.
| tts_errors   | true    | Optional     | Will speak errors on the selected cast device. For example: when the specified media wasn't found.
| aliases      |         | Optional     | Set alias names for your devices. Example below, set what you want to call it then it's actual name or machine ID.
| cast_delay   | 6       | Optional     | This delay helps prevent "Sorry, something went wrong" and grey screen errors. [See below for more info.](#cast-delay)

<hr>

**Sample Config**
```
plex_assistant:
  url: 'http://192.168.1.3:32400'
  token: 'tH1s1Sy0uRT0k3n'
  default_cast: 'Downstairs TV'
  language: 'en'
  tts_errors: true
  aliases:
    Downstairs TV: TV0565124
    Upstairs TV: Samsung_66585
```

## Companion Sensor

Plex Assistant includes a sensor to display the names of currently connected devices as well as the machine ID of Plex clients. This is to help with config and troubleshooting. To update the sensor send the command "update sensor" to Plex Assistant either through Google Assistant or as a HA service call.

```
sensor:
- platform: plex_assistant
```

***You must restart after installation and configuration, you may want to setup IFTTT or DialogFlow with the instructions below before doing so.*** 

## IFTTT/DialogFlow-Setup

You can either use IFTTT or DialogFlow to trigger Plex Assistant. IFTTT is the easiest way to set this up, DialogFlow is more involved and has some quirks. The advantage to using Dialogflow is it's support for more languages (as long as the translation has been made for Plex Assistant, see below).

#### Supported Languages
Plex Assistant currently supports: English (en), Swedish (sv), Dutch (nl), French (fr), and Italian (it) when using Dialogflow. [Help add translations.](#translation)

<details>
  <summary><b>IFTTT Setup Guide</b></summary>
  
## IFTTT Setup

#### In Home Assistant

* Go to "Configuration" in your HA sidebar and select "Integrations"
* Hit the add button and search for "IFTTT" and click configure.
* Follow the on screen instructions.
* Copy or save the URL that is displayed at the end, we'll need it later and it won't be shown again.
* Click "Finish"

#### In IFTTT

Visit [ifttt.com](https://ifttt.com/) and sign up or sign in.

* Click "Explore" in the top right, then hit the plus sign to make your own applet from scratch
* Press the plus sign next to "If". Search for and select "Google Assistant"
* Select "Say phrase with text ingredient"

Now you can select how you want to trigger this service, you can select up to 3 ways to invoke it. I use things like `tell plex to $` or `have plex $`. The dollar sign will be the phrase sent to this component. See currently supported [commands below](#commands)). You can also set a response from the Google Assistant if you'd like. Hit "Create Trigger" to continue.

* Press the plus sign next to "Then"
* Search for and select "Webhooks", then select "Make a web request"
* In the URL field enter the webhook URL HA provided you earlier
* Select method "Post" and content type "application/json"
* Then copy and paste the code below into the body field

`{ "action": "call_service", "service": "plex_assistant.command", "command": "{{TextField}}" }`

#### In Home Assistant

Finally, add the following automation to your Home Assistant configuration.yaml:

```
automation:
  - alias: Plex Assistant Automation
    trigger:
    - event_data:
        action: call_service
      event_type: ifttt_webhook_received
      platform: event
    condition:
      condition: template
      value_template: "{{ trigger.event.data.service == 'plex_assistant.command' }}"
    action:
    - data_template:
        command: "{{ trigger.event.data.command }}"
      service_template: '{{ trigger.event.data.service }}'
```

***Either refresh your automations or restart after adding the automation.***

</details>

<details>
  <summary><b>DialogFlow Setup Guide</b></summary>

## DialogFlow Setup

#### In Home Assistant

* Go to "Configuration" in your HA sidebar and select "Integrations"
* Hit the add button and search for "Dialogflow".
* Copy or save the URL that is displayed, we'll need it later and it won't be shown again.
* Click "Finish"

#### In DialogFlow

Visit https://dialogflow.com/ and sign up or sign in.
Keep going until you get to the "Welcome to Dialogflow!" page with "Create Agent" in the sidebar.

* Click on Create Agent and Type "Plex_Assistant" as the agent name and select "Create"
* Now select "Fulfillment" in the sidebar and enable "Webhook"
* Enter the "URL" Home Assistant provided us earlier, scroll down and click "Save"
* Now select "Intents" in the sidebar and hit the "Create Intent" button.
* Select "ADD PARAMETERS AND ACTION" and enter "Plex" as the action name.
* Check the checkbox under "Required"
* Under "Parameter Name" put "command", under "Entity" put "@sys.any", and under "Value" put "$command"
* Now click "ADD TRAINING PHRASES"
* Create a phrase and type in "command"
* Then double click on the word "command" you just entered and select "@sys.any:command"
* Scroll to the bottom and expand "Fulfillment" then click "ENABLE FULFILLMENT"
* Turn on "Enable webhook call for this intent"
* Expand "Responses" turn on “Set this intent as end of conversation”
* At the top of the page enter "Plex" for the intent name and hit "Save"
* On the right side of the page hit "Set-up Google Assistant integration"
* Click the space under "Explicit invocation", select "Plex", then hit "Close"
* Type "Plex" in "Implicit invocation", then click "Manage assistant app"
* Click "Decide how your action is invoked"
* Under "Display Name" type "Plex" then hit save in the top right (it may give an error, but thats okay).

#### In Home Assistant

Add the following to your `configuration.yaml` file

```
intent_script:
  Plex:
    speech:
      text: Command sent to Plex.
    action:
      - service_template: plex_assistant.command
        data_template:
          command: "{{command}}"
```

You can now trigger Plex Assistant by saying "Hey Google, tell plex to..." or "Hey Google, ask plex to..."

***Restart after adding the above.***

</details>

<details>
  <summary><b>Rhasspy Voice Assistant Setup Guide</b></summary>
  
## Rhasspy Setup

#### Pre Requistites
You already have setup Rhasspy Intent Handling to <b>Send Events</b> to Home assistant. If this has not been done, there is plenty of Rhasspy documentation on the subject depending on your setup. <b>Intents</b> can also be sent to home assistant but this is not covered here.
#### Rhasspy Setup
You will need to setup a Slot and Sentence in Rhasspy, one example shown below.
See the Rhasspy Documentation if more information is required on Slots and Sentences
#### Slot
Create a Slot called ‘Films’ and paste in or type your list of Film titles. The Rhasspy documentation shows how slots may be dynamically updated with scripts.
e.g.
```
Ant Man
Aquaman
Birdman
….
Wanted
Zero Dark 30
```
#### Sentence
Example:-
```
[PlayFilm]
play ($films) {film_name} (in | on) plex
```
In the above example, saying ‘Play Ant Man in Plex’ will match the sentence and play the film. Note that ‘in’ can also be ‘on’ due to the alternative defined (in | on). $films refers to our slot list of films, and {film_name} is the tag that will store our film name and pass to Home Assistant. Also note that the sentence will only match if our film is in the slot list.

### Home assistant
#### Automation
Example trigger / action :-
```
  trigger:
  - event_data: {}
    event_type: rhasspy_PlayFilm
    platform: event
  condition: []
  action:
  - data_template:
      command: '{% set plex_command = "play " + trigger.event.data.film_name %} {{
        plex_command }}'
    service: plex_assistant.command
```

The event defined in the trigger is rhasspy_PlayFilm where we defined [PlayFilm] as our sentence in Rhasspy. Our film_name tag declared in Rhasspy can be accessed in the event data - trigger.event.data.film_name

#### Troubleshooting

In Home assistant, Developer Tools, select the Events tab. At the bottom, you can listen to events. Put rhasspy_PlayFilm as the event to subscribe to and click ‘start listening’.

When the event is fired you should see something like this (first few lines of the event). Note the film_name, intentName, sitteid, slots and so on are all useful. Particularly film_name though.
```
Event 4 fired 11:34 AM:

{
    "event_type": "rhasspy_PlayFilm",
    "data": {
        "film_name": "Ant Man",
        "_text": "play Ant Man in plex",
        "_raw_text": "play ant man in plex",
        "_intent": {
            "input": "play Ant Man in plex",
            "intent": {
                "intentName": "PlayFilm",
                "confidenceScore": 1
            },
            "siteId": "living_room",
            "id": null,
            "slots": [
                {
                    "entity": "films",
                    "value": {
                        "kind": "Unknown",
                        "value": "Ant Man"
                    },
                    "slotName": "film_name",
                    "rawValue": "ant man",
……..
…….
```
</details>

## Commands

#### Fuzzy Matching
A show or movie's title and the Chromecast device used in your phrase are processed using a fuzzy search. Meaning it will select the closest match using your Plex media titles and available cast device names. `"play walk in deed on the dawn tee"` would become `"Play The Walking Dead on the Downstairs TV."`. This even works for partial matches. `play Pets 2` will match `The Secret Life of Pets 2`.

#### You can say things like:
* `"play the latest episode of Breaking Bad on the Living Room TV"`
* `"play unwatched breaking bad"`
* `"play Breaking Bad"`
* `"play Pets 2 on the Kitchen Chromecast"`
* `"play ondeck"`
* `"play ondeck movies"`
* `"play season 1 episode 3 of The Simpsons"`
* `"play first season second episode of Taskmaster on the Theater System"`

### Control Commands:
* `play`
* `pause`
* `stop`
* `jump forward`
* `jump back`

Be sure to add the name of the device to control commands if it is not the default device. `"stop downstairs tv"`.

I've tried to take into account many different ways that commands could be phrased. If you find a phrase that isn't working and you feel should be implemented, please make an issue.

***Music isn't built in yet, only shows and movies at the moment.***

#### Cast Device
If no cast device is specified the default_cast device set in config is used. A cast device will only be found if at the end of the command and when preceded with the word `"on"` or words `"on the"`. Example: *"play friends **ON** downstairs tv"*

## Cast Delay
A delay (in seconds) is used to help prevent grey screen and "Sorry, something went wrong" errors that can happen on some cast devices. This setting has no effect on Plex Clients, only Google Cast devices.

If you are having these issues you can test the delay needed by using the `plex_assistant.command` service found in `Developer Tools > Services`. The example below will test the needed delay on the device named "Downstairs TV":

```
command: Play Evil Dead on the Downstairs TV
cast_delay: 7
```

The amount of delay needed is typically the time it takes from when the screen turns black after calling the service to when you see the show info on screen. Test this with nothing playing on the device and with something already playing on the device as well.

The default delay per device is 6 seconds. By using this config option you can set the delay per device, see example below:

```
plex_assistant:
  url: 'http://192.168.1.3:32400'
  token: 'tH1s1Sy0uRT0k3n'
  default_cast: 'Downstairs TV'
  cast_delay:
    Downstairs TV: 7
```


## Translation
You can contribute to the translation/localization of this component by using the [translation guide](translation.md).
