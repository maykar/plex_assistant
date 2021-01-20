## Troubleshooting Plex Assistant

Whenever posting an issue always include the following info: 

* Any errors in your logs
* The method you're using (IFTTT, DialogFlow, HA Conversation)
* If the companion sensor is working
* If you're able to use HA's built in Plex Integration without issue
* Any helpful info from the troubleshooting methods below

## Test via services

Test to see if everything works via services:
* In your HA sidebar select "Developer Tools"
* Then click "Services"
* Type `plex_assistant.command` into the service field
* Click "Fill Example Data" at the bottom
* Modify the example data to fit your needs and hit "Call Service"

## Enable debug logs for the component

Add the following to your configuration.yaml file, restart, ask plex assistant to do something, go to your logs and view full logs.

```
logger:
  logs:
    custom_components.plex_assistant: debug
```

## Add a debug line to your Plex Assistant triggers:

Add a line to your Plex Assistant automation or intent script that will post the command it recieves to your logs:

#### IFTTT Automation

```
alias: Plex Assistant Automation
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
  ###################################################
  # The following 4 lines are the added debug lines #
  ###################################################
- service: system_log.write
  data:
    message: "{{ trigger.event.data.command }}"
    level: warning
```

#### DialogFlow Intent Script

```
intent_script:
  Plex:
    speech:
      text: "Command sent to Plex."
    action:
      - service: plex_assistant.command
        data:
          command: "{{command}}"
        ###################################################
        # The following 4 lines are the added debug lines #
        ###################################################
      - service: system_log.write
        data:
          message: "{{ command }}"
          level: warning
```
