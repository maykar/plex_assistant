## Troubleshooting Plex Assistant

Whenever posting an issue always include the following info: 

* Any errors in your logs
* The method you're using (IFTTT, DialogFlow, HA Conversation)
* If the companion sensor is working
* If you're able to use HA's built in Plex Integration without issue
* Any helpful info from the troubleshooting methods below

## Enable debug logs for the component

Add the following to your configuration.yaml file, restart, ask plex assistant to do something, go to your logs and view full logs.

```
logger:
  logs:
    custom_components.plex_assistant: debug
```


#### DialogFlow Intent Script
If you use DialogFlow, add a line to your Plex Assistant intent script that will post the command it recieves to your logs:

```
intent_script:
  Plex:
    speech:
      text: "Command sent to Plex."
    action:
      - service: plex_assistant.command
        data:
          command: "{{command}}"
####### The following 4 lines are for the debug service.
      - service: system_log.write
        data:
          message: "Plex Assistant Command: {{ command }}"
          level: warning
```
