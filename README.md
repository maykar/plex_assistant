# ❱ Plex Assistant

[Installation](#installation) ｜ [Configuration](#configuration) ｜ [IFTTT Setup](#ifttt-setup) ｜ [Commands](#commands) ｜ [Translations](#translation)<br><hr>

Plex Assistant is a Home Assistant component to allow Google Assistant to cast Plex media to Google cast devices with a bit of help from [IFTTT](https://ifttt.com/).

Example: `"Hey Google, tell Plex to play The Walking Dead on the Downstairs TV."`

You can use the component's service without IFTTT as well to call the commands however you'd like. Visit the services tab in HA's Developer Tools to test it out.

#### Support Development
- :coffee:&nbsp;&nbsp;[Buy me a coffee](https://www.buymeacoffee.com/FgwNR2l)
- :heart:&nbsp;&nbsp;[Sponsor me on GitHub](https://github.com/sponsors/maykar)
- :keyboard:&nbsp;&nbsp;Help with translation, development, or documentation

## Author's note
This is just a side project made to fill the absence of native Google Assistant support in Plex and because the Phlex/FlexTV projects aren't in working order at the moment (is it just me?). It has only been tested on my setup with first generation Chromecasts.

This project is not a priority as Plex could add Google Assistant support or FlexTV may become viable again at any time. That being said, I will be adding features and fixing issues until that time. As always, I both welcome and greatly appreciate pull requests.

Thank you for understanding.

## Installation
Install by using one of the methods below:

* **Install with [HACS](https://hacs.xyz/):** Search integrations for "Plex Assistant", select and hit install. Add the configuration (see below) to your configuration.yaml file.

* **Install Manually:** Install this component by copying all of [these files](https://github.com/maykar/plex_assistant/tree/master/custom_components/plex_assistant) to `/custom_components/plex_assistant/`. Add the configuration (see below) to your configuration.yaml file.

## Configuration
Add config to your configuration.yaml file.

| Key          | Default | Necessity | Description
| :--          | :------ | :-------- | :----------
| url          |         | **Required** | The full url to your Plex instance including port.
| token        |         | **Required** | Your Plex token. [How to find your Plex token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/).
| default_cast |         | Optional     | The name of the cast device to use if none is specified.
| language     | 'en'    | Optional     | Language code. Currently only 'en' (english) is supported.
| tts_errors   | true    | Optional     | Will speak errors on the selected cast device. For example: when the specified media wasn't found.

<hr>

**Sample Config**
```
plex_assistant:
  url: 'http://192.168.1.3:32400'
  token: 'tH1s1Sy0uRT0k3n'
  default_cast: 'Downstairs TV'
  language: 'en'
  tts_errors: true
```

***You must restart after installation and configuration, you may want to add IFTTT config below before doing so.*** 

## IFTTT Setup

If you haven't set up IFTTT with HA yet, go to "Configuration" in your sidebar and then "Integrations", add a new integration and search for IFTTT. Click on configure, then follow the instructions on the screen.

This will provide you with a webhook URL to use in your IFTTT applet. Make sure to copy this, leave the window open, or save it in some way for later use.

* Go to [ifttt.com](https://ifttt.com/) and login or create an account
* Click "Explore" in the top right, then hit the plus sign to make your own applet from scratch
* Press the plus sign next to "If". Search for and select "Google Assistant"
* Select "Say phrase with text ingredient"

Now you can select how you want to trigger this service, you can select up to 3 ways to invoke it. I use things like `tell plex to $` or `have plex $`. The dollar sign will be the phrase sent to this component. This component expects to hear something starting with "play" followed by at least a show/movie name, "ondeck", or similar (see more about [commands below](#commands)). You can also set a response from the Google Assistant if you'd like. Hit "Create Trigger" to continue.

* Press the plus sign next to "Then"
* Search for and select "Webhooks", then select "Make a web request"
* In the URL field enter the webhook URL HA provided you earlier
* Select method "Post" and content type "application/json"
* Then copy and paste the code below into the body field

`{ "action": "call_service", "service": "plex_assistant.command", "command": "{{TextField}}" }`

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

I've tried to take into account many different ways that commands could be phrased. If you find a phrase that isn't working and you feel should be implemented, please make an issue.

***Music isn't built in yet, only shows and movies at the moment.***

#### Cast Device
If no cast device is specified the default_cast device set in config is used. A cast device will only be found if at the end of the command and when preceeded with the phrase `"on the"`. Example: *"play friends **ON THE** downstairs tv"*

## Translation
You can contribute to the translation/localization of this component by using the [translation guide](translation.md).
