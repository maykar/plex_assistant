# ❱ Plex Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-yellow.svg)](https://github.com/custom-components/hacs) [![hacs_badge](https://img.shields.io/badge/Buy-Me%20a%20Coffee-critical)](https://www.buymeacoffee.com/FgwNR2l)

[Installation](#installation) ｜ [Configuration](#configuration) ｜ [Cast Devices](#cast-devices) ｜ [Commands](#commands)<br>
[Google Assistant Triggers](#google-assistant-triggers) ｜ [HA Conversation Setup](#home-assistant-conversation-setup)<br><hr>

Plex Assistant is a Home Assistant component to allow Google Assistant, Home Assistant's conversation integration, and more to cast Plex media to Google devices and Plex clients. You could use this component with anything that can make a service call to HA as well (see the automations in the [Google Assistant trigger guides](](#google-assistant-triggers)) for IFTTT and DialogFlow as a starting point).

Example: `"Hey Google, tell Plex to play The Walking Dead on the Downstairs TV."`

You can use the component's service (`plex_assistant.command`) to call the commands however you'd like. Visit the services tab in HA's Developer Tools to test it out.

Example [HA service call](https://www.home-assistant.io/docs/scripts/service-calls/):
```
service: plex_assistant.command
data:
  command: Play Breaking Bad
```

***Music and audio aren't built in yet, only shows and movies at the moment.***

## Supporting Development
- :coffee:&nbsp;&nbsp;[Buy me a coffee](https://www.buymeacoffee.com/FgwNR2l)
- :heart:&nbsp;&nbsp;[Sponsor me on GitHub](https://github.com/sponsors/maykar)
- :keyboard:&nbsp;&nbsp;Help with [translation](translation.md), development, or documentation
  <br><br>

## Installation
Install by using one of the methods below:

* **Install with [HACS](https://hacs.xyz/):** Search integrations for "Plex Assistant", select and hit install. Add the configuration (see below) to your configuration.yaml file.

* **Install Manually:** Install this component by copying all of [these files](https://github.com/maykar/plex_assistant/tree/master/custom_components/plex_assistant) to `/custom_components/plex_assistant/`. Add the configuration (see below) to your configuration.yaml file.

## Configuration
Add config to your configuration.yaml file.

| Key          | Default | Necessity    | Description
| :--          | :------ | :--------    | :----------
| url          |         | **Required** | The full url to your Plex instance including port. [Info for SSL connections here](#ssl-url).
| token        |         | **Required** | Your Plex token. [How to find your Plex token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/).
| default_cast |         | Optional     | The name of the cast device to use if none is specified.
| language     | 'en'    | Optional     | Language code ([Supported Languages](#currently-supported-languages)).
| tts_errors   | true    | Optional     | Will speak errors on the selected cast device. For example: when the specified media wasn't found.
| aliases      |         | Optional     | Set alias names for your devices. Example below, set what you want to call it then it's actual name or machine ID.

<hr>

**Sample Config**
```yaml
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

## Cast Devices
This component does not use HA's media_player entities, it automatically detects compatible devices (Google Cast devices and Plex Clients). It will use the name from the devices themselves. Use the [companion sensor](#companion-sensor) to get a list of compatible devices with their names/IDs.

## Companion Sensor

Plex Assistant includes a sensor to display the names of currently connected devices as well as the machine ID of Plex clients. This is to help with config and troubleshooting.

Add the sensor by including the code below in your configuration.yaml file.

```yaml
sensor:
- platform: plex_assistant
```

To update the sensor send the command "update sensor" to Plex Assistant either through your voice assistant (e.g. `"Hey Google, tell Plex to update sensor."`) or as a HA service call. The sensor is also updated any time Plex Assistant is sent a command. To view the sensor results, navigate to "Developer Tools" in HA's sidebar and click "States", then find `sensor.plex_assistant_devices` in the list below.

Plex clients must be open in order to be detected or recieve commands from this component, Plex can sometimes take around a minute to detect that a client is active/inactive.

***You must restart after installation and configuration, you may want to setup Google Assistant triggers or HA's conversation intergration first as they will also require a restart. Instructions for each below.*** 

## Google Assistant Triggers

You can either use IFTTT or DialogFlow to trigger Plex Assistant with Google Assistant. IFTTT is the easiest way to set this up, but only if IFTTT supports your language. DialogFlow is a bit more involved and has some quirks, but has support for more languages.

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

* Create a new applet
* Click "Add" next to "If This". Search for and select "Google Assistant"
* Select "Say phrase with text ingredient"

Now you can select how you want to trigger this service, you can select up to 3 ways to invoke it. I use things like `tell plex to $` or `have plex $`. The dollar sign will be the phrase sent to this component. See currently supported [commands below](#commands)). You can also set a response from the Google Assistant if you'd like. Select your language (as long as it's supported, see list above), then hit "Create Trigger" to continue.

* Click "Add" next to "Then That"
* Search for and select "Webhooks", then select "Make a web request"
* In the URL field enter the webhook URL HA provided you earlier
* Select method "Post" and content type "application/json"
* Then copy and paste the code below into the body field

`{ "action": "call_service", "service": "plex_assistant.command", "command": "{{TextField}}" }`

#### In Home Assistant

Finally, add the automation either by using the YAML code or the Blueprint below:

<details>
  <summary><b>Automation Blueprint</b></summary>

* Go to "Configuration" in your sidebar
* Click "Blueprints", then "Import Blueprint"
* Paste this into the URL field `https://gist.github.com/maykar/11f46cdfab0562e683557403b2aa88b4`
* Click "Preview Blueprint", then "Import Blueprint"
* Find "Plex Assistant IFTTT Automation" in the list and click "Create Automation"
* Type anything on the last line (HA currently requires any interaction to save)
* Hit "Save"

</details>

<details>
  <summary><b>Automation YAML</b></summary>

```yaml
alias: Plex Assistant Automation
trigger:
- platform: event
  event_type: ifttt_webhook_received
  event_data:
    action: call_service
condition:
  condition: template
  value_template: "{{ trigger.event.data.service == 'plex_assistant.command' }}"
action:
- service: "{{ trigger.event.data.service }}"
  data:
    command: "{{ trigger.event.data.command }}"
```

</details>

If you prefer Node Red to HA's automations, @1h8fulkat has shared a [Node Red Flow](https://github.com/maykar/plex_assistant/issues/34) to do this.

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

Visit https://dialogflow.cloud.google.com/ and sign up or sign in.
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
* On the left side of the page hit "Integrations", then "Integration Settings"
* Click the space under "Explicit invocation", select "Plex"
* Type "Plex" in "Implicit invocation"
* You may need to hit the test button and accept terms of service before next step
* Click "Manage assistant app", then "Decide how your action is invoked"
* Under "Display Name" type "Plex" then hit save in the top right (it may give an error, but thats okay).

#### In Home Assistant

Add the following to your `configuration.yaml` file

```yaml
intent_script:
  Plex:
    speech:
      text: "Command sent to Plex."
    action:
      - service: plex_assistant.command
        data:
          command: "{{command}}"
```

You can now trigger Plex Assistant by saying "Hey Google, tell plex to..." or "Hey Google, ask plex to..."

***Restart after adding the above.***

</details>

### Currently Supported Languages:
| Language |  Code  |        IFTTT         |         DialogFlow         |
|:----------|:------:|:--------------------:|:--------------------------:|
| <img src='https://raw.githubusercontent.com/yammadev/flag-icons/master/png/NL%402x.png?raw=true' height='12'>&nbsp;&nbsp;&nbsp;**Dutch**    | `"nl"` |         :x:          |      :heavy_check_mark:    |
| <img src='https://raw.githubusercontent.com/yammadev/flag-icons/master/png/GB%402x.png?raw=true' height='12'>&nbsp;&nbsp;&nbsp;**English**  | `"en"` |  :heavy_check_mark:  |      :heavy_check_mark:    |
| <img src='https://raw.githubusercontent.com/yammadev/flag-icons/master/png/FR%402x.png?raw=true' height='12'>&nbsp;&nbsp;&nbsp;**French**   | `"fr"` |  :heavy_check_mark:  |      :heavy_check_mark:    |
| <img src='https://raw.githubusercontent.com/yammadev/flag-icons/master/png/DE%402x.png?raw=true' height='12'>&nbsp;&nbsp;&nbsp;**German**  | `"de"` |  :heavy_check_mark:  |      :heavy_check_mark:    |
| <img src='https://raw.githubusercontent.com/yammadev/flag-icons/master/png/IT%402x.png?raw=true' height='12'>&nbsp;&nbsp;&nbsp;**Italian**  | `"it"` |  :heavy_check_mark:  |      :heavy_check_mark:    |
| <img src='https://raw.githubusercontent.com/yammadev/flag-icons/master/png/SV%402x.png?raw=true' height='12'>&nbsp;&nbsp;&nbsp;**Swedish**  | `"sv"` |         :x:          |      :heavy_check_mark:    |
| <img src='https://raw.githubusercontent.com/yammadev/flag-icons/master/png/DK%402x.png?raw=true' height='12'>&nbsp;&nbsp;&nbsp;**Danish**  | `"da"` |         :x:          |      :heavy_check_mark:    |

#### [Help add support for more languages.](translation.md)<hr>

## Home Assistant Conversation Setup

To use Plex Assistant with Home Assistant's conversation integration simply add the code below to your configuration.yaml file. Using the conversation integration will work with any of the languages from the table above.

```yaml
conversation:
  intents:
    Plex:
     # These trigger commands can be changed to suit your needs.
     - "Tell Plex to {command}"
     - "{command} with Plex"

intent_script:
  Plex:
    speech:
      text: Command sent to Plex.
    action:
      service: plex_assistant.command
      data:
        command: "{{command}}"
```

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

If no cast device is specified in your command, the `default_cast` device set in your config is used. A cast device will only be found if at the end of the command and when preceded with the word `"on"` or words `"on the"`. Example: *"play friends **ON** downstairs tv"*

I've tried to take into account many different ways that commands could be phrased. If you find a phrase that isn't working and you feel should be implemented, please make an issue.

### SSL URL
If you use the Plex server network setting of "Required" for "Secure Connections" and do not provide a custom certificate, you need to use your plex.direct URL in the settings. You can find it using the steps below:

* Go to https://app.plex.tv/ and sign in.
* Hit the vertical 3 dots in the bottom right of any media item (episode, movie, etc)
* Select "Get Info", then click "View XML"
* The URL field of your browser now contains your plex.direct URL
* Copy everything before "/library"
* It will look something like this: `https://192-168-10-25.xxxxxxxxxxxxxxxxx.plex.direct:32400`

If you use a custom certificate, use the URL that the certificate is for.
