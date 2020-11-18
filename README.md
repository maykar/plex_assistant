# ❱ Plex Assistant

[Installation](#installation) ｜ [Configuration](#configuration) ｜ [Cast Devices](#cast-devices) ｜ [Google Assistant Triggers](#google-assistant-triggers) ｜ [Commands](#commands) ｜ [HA Conversation Setup](#home-assistant-conversation-setup)<br><hr>

Plex Assistant is a Home Assistant component to allow Google Assistant, Home Assistant's conversation integration, and more to cast Plex media to Google devices and Plex clients. You could use this component with anything that can make a service call to HA as well (see the automations in the [Google Assistant trigger guides](](#google-assistant-triggers)) for IFTTT and DialogFlow as a starting point).

Example: `"Hey Google, tell Plex to play The Walking Dead on the Downstairs TV."`

You can use the component's service (`plex_assistant.command`) to call the commands however you'd like. Visit the services tab in HA's Developer Tools to test it out.

Example [HA service call](https://www.home-assistant.io/docs/scripts/service-calls/):
```
service: plex_assistant.command
data:
  command: Play Breaking Bad
```

I've tried to take into account many different ways that commands could be phrased. If you find a phrase that isn't working and you feel should be implemented, please make an issue.

***Music and audio aren't built in yet, only shows and movies at the moment.***

## Supporting Development
- :coffee:&nbsp;&nbsp;[Buy me a coffee](https://www.buymeacoffee.com/FgwNR2l)
- :1st_place_medal:&nbsp;&nbsp;[Tip some Crypto](https://github.com/sponsors/maykar)
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
| remote_server| false   | Optional     | If the Plex server used is not on your local network, set this to true. [More info below.](#remote-server-setting)

<hr>

**Sample Config**
The sample config below contains some default values (noted above). Any option that you use the default value of does not need to be included in your config at all. It is just placed in the example to illustrate proper config.

```yaml
plex_assistant:
  url: "http://192.168.1.3:32400"
  token: "tH1s1Sy0uRT0k3n"
  default_cast: "Downstairs TV"
  language: "en"
  tts_errors: true
  sensor: true
  aliases:
    Downstairs TV: "TV0565124"
    Upstairs TV: "Samsung_66585"
```

## Cast Devices
This component does not use HA's media_player entities, it automatically detects compatible devices (Google cast devices and Plex clients). It will use the name from the devices themselves. Use the companion sensor (mentioned below) to get a list of compatible devices with their names and other info.

If no cast device is specified in your command, the `default_cast` device set in your config is used. A cast device will only be found if at the end of the command and when preceded with the word `"on"` or words `"on the"`. Example: *"play friends **ON** downstairs tv"*

## Companion Sensor

To help with config and troubleshooting Plex Assistant automatically adds a sensor to display the names of connected Google cast devices and Plex clients. It will also display the machine ID and type of device for Plex clients.

To update the sensor send the command "update sensor" to Plex Assistant either through your voice assistant (e.g. `"Hey Google, tell Plex to update sensor."`) or as a HA service call. The sensor will also update any time a command is sent to Plex Assistant and at HA startup.

To view the sensor results, navigate to "Developer Tools" in HA's sidebar and click "States", then find `sensor.plex_assistant_devices` in the list below.

Note: Plex clients must be open in order to be detected by the sensor or recieve commands from this component, Plex can sometimes take around a minute to detect that a client is active/inactive.

***You must restart after installation and configuration, but you may want to setup Google Assistant triggers or HA's conversation intergration first as they will also require a restart. Instructions for each below.*** 

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

* Click "Explore" in the top right, then hit the plus sign to make your own applet from scratch
* Press the plus sign next to "If". Search for and select "Google Assistant"
* Select "Say phrase with text ingredient"

Now you can select how you want to trigger this service, you can select up to 3 ways to invoke it. I use things like `"tell plex to $"` or `"$ with plex"`. The dollar sign will be the phrase sent to this component. See currently supported [commands below](#commands)). You can also set a response from the Google Assistant if you'd like. Select your language (as long as it's supported, see list above), then hit "Create Trigger" to continue.

* Press the plus sign next to "Then"
* Search for and select "Webhooks", then select "Make a web request"
* In the URL field enter the webhook URL HA provided you earlier
* Select method "Post" and content type "application/json"
* Then copy and paste the code below into the body field

`{ "action": "call_service", "service": "plex_assistant.command", "command": "{{TextField}}" }`

#### In Home Assistant

Finally, add the following automation to your Home Assistant configuration.yaml.
**Note**: If you already have an `automation:` section in your config just copy and paste everything after `automation:` into that section:

```yaml
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
    - service: "{{ trigger.event.data.service }}"
      data:
        command: "{{ trigger.event.data.command }}"
```

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
* Enter the URL Home Assistant provided us earlier, scroll down and click "Save"
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

Add the following to your `configuration.yaml` file.
**Note**: If you already have an `intent_script:` section in your config just copy and paste everything after `intent_script:` into that section:

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

<!---
| <img src='https://raw.githubusercontent.com/yammadev/flag-icons/master/png/DA%402x.png?raw=true' height='12'>&nbsp;&nbsp;&nbsp;**Danish**  | `"da"` |         :x:          |      :heavy_check_mark:    |
-->

#### [Help add support for more languages.](translation.md)<hr>

## Home Assistant Conversation Setup

To use Plex Assistant with Home Assistant's conversation integration simply add both the code blocks below to your configuration.yaml file. Using the conversation integration will work with any of the languages from the table above.

**Note**: If you already have an `conversation:`section in your config just copy and paste everything after `conversation:` into that section or if you already have an `intents:` section in the `conversation:` section copy everything under `intents:` and paste it into the `intents:` section:

```yaml
conversation:
  intents:
    PlexAssistant:
     # These trigger commands can be changed to suit your needs.
     - "Tell Plex to {command}"
     - "{command} with Plex"
```

**Note**: If you already have an `intent_script:`section in your config just copy and paste everything after `intent_script:` into that section or if you have already setup the intent script for Dialog flow, this is the same intent script (no need to add it again).

```
intent_script:
  Plex:
    speech:
      text: Command sent to Plex.
    action:
      service: plex_assistant.command
      data_template:
        command: "{{command}}"
```

## Commands

#### Fuzzy Matching
A show or movie's title and the cast device used in your phrase are processed using a fuzzy search. Meaning it will select the closest match using your Plex media titles and available cast device names. `"play walk in deed on the dawn tee"` would become `"Play The Walking Dead on the Downstairs TV."`. This even works for partial matches. `play Pets 2` will match `The Secret Life of Pets 2`.

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

### Remote Server Setting:

In order to cast to local Plex clients while using this integration with a remote Plex server (one not on your local network) you need to use the config option `remote_server: true`.

This finds your Plex clients by using a remote API call to plex.tv . This can increase loading/call times and requires the plex.tv API to be up and available, but this is the only way to allow casting between a remote Plex server and a Plex client on your local network.

### SSL URL

If you use the Plex server network setting of "Required" for "Secure Connections" and do not provide a custom certificate, you need to use your plex.direct URL in the settings. You can find it using the steps below:

* Go to https://app.plex.tv/ and sign in.
* Hit the vertical 3 dots in the bottom right of any media item (episode, movie, etc)
* Select "Get Info", then click "View XML"
* The URL field of your browser now contains your plex.direct URL
* Copy everything before "/library"
* It will look something like this: `https://192-168-10-25.xxxxxxxxxxxxxxxxx.plex.direct:32400`

If you use a custom certificate, use the URL that the certificate is for.
