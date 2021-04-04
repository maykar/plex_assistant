## Troubleshooting Plex Assistant

Whenever posting an issue include as much of the following info as you can: 

* Any errors related to Plex Assistant or Plex in your logs along with debug info (see below on how to enable debug)
* The trigger method you're using (IFTTT, DialogFlow, or HA Conversation)
* The method used to install (HACS or manually)
* If HA's Plex Integration works without issue
* The command you are using (if the issue is command specific)
* If using the `plex_assistant.command` service in HA's Developer Tools is working
* Config options if relevant
* If you're using advanced config, show the config you're using

## Enable debug logs for the component

Add the following to your configuration.yaml file, restart, ask plex assistant to do something, go to your logs and view full logs.

```yaml
logger:
  default: warning
  logs:
    custom_components.plex_assistant: debug
```
