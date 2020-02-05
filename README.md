# Plex Assistant
Home Assistant Component to allow Google Assistant to cast Plex to Chromecasts with a bit of help from IFTTT.

This component adds a service to Home Assistant that when called will take commands to cast Plex to a Chromecast/Google Home/Google Nest device.

This can be used with the HA IFTTT integration to allow you to speak these commands to Google Assistant.

## Installation

## IFTTT Setup

If you haven't set up IFTTT with HA yet, go to the integrations page in the configuration screen and find IFTTT. Click on configure. Follow the instructions on the screen to configure IFTTT.

This will provide you with a webhook URL to use in your IFTTT applet. Make sure to copy this or save it.

* Go to IFTTT.com and click "Explore" in the top right, then the plus sign to make your own applet from scratch
* Press the plus sign next to "If" then search for "Google Assistant" and select it
* Select "Say phrase with text ingredient"

Now you can select how you want to trigger this service, you can select up to 3 ways to invoke it. I use things like `tell plex to $`.
The dollar sign will be the phrase sent to this component. You can also set a response from the Google Assistant if you'd like.

* Hit "Create Trigger", the press the plus sign next to "Then"
* Search for "Webhooks" and select it, then select "Make a web request"
* In the URL field enter the webhook URL HA provided us.
* Select method "Post" and content type "application/json"
* Then copy and paste the code below into the body field

```{ "action": "call_service", "service": "plex_assistant.command", "command": " {{TextField}}" }```

Finally add this automation to your Home Assistant configuration.yaml:

```
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
