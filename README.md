# ❱ Plex Assistant

[Installation](#installation) ｜ [Configuration](#configuration) ｜ [Cast Devices](#cast-devices) ｜ [Commands](#commands)<br>
[Google Assistant Triggers](#google-assistant-triggers) ｜ [HA Conversation Setup](#home-assistant-conversation-setup)<br><hr>

Plex Assistant is a Home Assistant component to allow Google Assistant, Home Assistant's conversation integration, and more to cast Plex media to Google devices and Plex clients. You could use this component with anything that can make a service call to HA as well (see the automations in the [Google Assistant trigger guides](](#google-assistant-triggers)) for IFTTT and DialogFlow as a starting point).

Example: `"Hey Google, tell Plex to play The Walking Dead on the Downstairs TV."`

You can use the component's service to call the commands however you'd like. Visit the services tab in HA's Developer Tools to test it out.

***Music and audio aren't built in yet, only shows and movies at the moment.***

## Supporting Development
- :coffee:&nbsp;&nbsp;[Buy me a coffee](https://www.buymeacoffee.com/FgwNR2l)
- :1st_place_medal:&nbsp;&nbsp;[Tip some Crypto](https://github.com/sponsors/maykar)
- :heart:&nbsp;&nbsp;[Sponsor me on GitHub](https://github.com/sponsors/maykar)
- :keyboard:&nbsp;&nbsp;Help with translation, development, or documentation
  <br><br>

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

## Cast Devices
This component does not use HA media players as devices, it automatically detects compatible devices (Google Cast devices and Plex Clients). It will use the name from the devices themselves. Use the [companion sensor](#companion-sensor) to get a list of compatible devices with their names/IDs.

## Companion Sensor

Plex Assistant includes a sensor to display the names of currently connected devices as well as the machine ID of Plex clients. This is to help with config and troubleshooting. To update the sensor send the command "update sensor" to Plex Assistant either through Google Assistant or as a HA service call. The sensor is also updated any time Plex Assistant is sent a command. To view the sensor results, navigate to "Developer Tools" in HA's sidebar and click "States", then find `sensor.plex_assistant_devices` in the list below.

Add the sensor by including the code below in your configuration.yaml file.

```
sensor:
- platform: plex_assistant
```

***You must restart after installation and configuration, you may want to setup Google Assistant triggers or HA's conversation intergration first as they will also require a restart. Instructions for each below.*** 

## Google Assistant Triggers

You can either use IFTTT or DialogFlow to trigger Plex Assistant with Google Assistant. IFTTT is the easiest way to set this up, but only if IFTTT supports your language. DialogFlow is a bit more involved and has some quirks, but has support for more languages (as long as the translation has been made for Plex Assistant).

**IFTTT currently supports the following languages:**

* English
* French
* German
* Italian
* Japanese
* Spanish

**Plex Assistant currently supports the following languages when using DialogFlow:**

* `"nl"` Dutch
* `"en"` English
* `"fr"` French
* `"it"` Italian
* `"sv"` Swedish

[Help add translations.](translation.md)<br><hr>

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

## Home Assistant Conversation Setup

To use Plex Assistant with Home Assistant's conversation integration simply add the code below to your configuration.yaml file:

```yaml
conversation:
  intents:
    PlexAssistant:
     # These trigger commands can be changed to suit your needs.
     - Tell Plex to {command}
     - {command} with Plex

intent_script:
  PlexAssistant:
    speech:
      text: Command sent to Plex.
    action:
      service: plex_assistant.command
      data_template:
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
