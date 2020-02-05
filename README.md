# Plex Assistant
Home Assistant Component to allow Google Assistant to cast Plex to Chromecasts with a bit of help from IFTTT.

This component adds a service to Home Assistant that when called with IFTTT on a Google Assistant will take commands to cast Plex to a Chromecast/Google Home/Google Nest device.

Example: `Hey Google, tell Plex to play The Walking Dead on the Downstairs TV`

You can use the component's service without IFTTT as well to call the commands however you'd like.

## Installation
...

## Config
Add to your configuration.yaml ([find your Plex token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)):
```
plex_assistant:
  url: 'http://192.168.1.3:32400' # URL to your Plex instance
  token: 'tH1s1Sy0uRT0k3n'        # Your Plex token
  default_cast: 'Downstairs TV'   # Cast device to use if none is specified in command.
```

## IFTTT Setup

If you haven't set up IFTTT with HA yet, go to the integrations page in the configuration screen and find IFTTT. Click on configure, then follow the instructions on the screen.

This will provide you with a webhook URL to use in your IFTTT applet. Make sure to copy this or save it.

* Go to IFTTT.com and click "Explore" in the top right, then hit the plus sign to make your own applet from scratch
* Press the plus sign next to "If" and search for "Google Assistant" then select it
* Select "Say phrase with text ingredient"

Now you can select how you want to trigger this service, you can select up to 3 ways to invoke it. I use things like `tell plex to $` or `have plex $`. The dollar sign will be the phrase sent to this component. This component expects to hear something starting with "play" followed by at least a show/movie name (see more about commands below). You can also set a response from the Google Assistant if you'd like.

* Hit "Create Trigger", the press the plus sign next to "Then"
* Search for "Webhooks" and select it, then select "Make a web request"
* In the URL field enter the webhook URL HA provided you.
* Select method "Post" and content type "application/json"
* Then copy and paste the code below into the body field

```{ "action": "call_service", "service": "plex_assistant.command", "command": " {{TextField}}" }```

Finally add this automation to your Home Assistant configuration.yaml:

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

## Commands

#### Fuzzy Matching
The show/movie title and chromecast device used in your phrase are processed using a fuzzy search. Meaning you can say something like `play walk in deed on dawn tee` and it will select the closest match `play The Walking Dead on Downstairs TV`.

#### You can say things like:
* `play the latest episode of Breaking Bad on the Living Room TV`
* `play unwatched breaking bad`  ( will use default chromecast from config )
* `play Breaking Bad`
* `play Pets 2 on the Kitchen Chromecast` ( Should automatically match "Secret Life of Pets 2" )

Season and Episode selection aren't built in yet.
