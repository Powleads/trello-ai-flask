# JustGoingViral MCP Configuration Update

The JustGoingViral server is not connected because it needs to be configured to run from the new location.

## Update Required in MCP Settings

You need to update your Cline MCP settings to change the path from the old location to the new one.

### Old Configuration (needs to be updated):
```json
"JustGoingViral": {
  "command": "node",
  "args": ["/Users/dbsal/Documents/Cline/MCP/JustGoingViral/dist/index.js"]
}
```

### New Configuration (use this):
```json
"JustGoingViral": {
  "command": "node",
  "args": ["/Users/dbsal/Documents/GitHub/JustGoingViral/dist/index.js"]
}
```

## Steps to Update:

1. Open VSCode Settings (Cmd+,)
2. Search for "MCP" or "Cline MCP"
3. Find the MCP Server Configurations
4. Update the JustGoingViral server path as shown above
5. Save the settings
6. Restart VSCode or reload the window (Cmd+Shift+P → "Developer: Reload Window")

## After Update:

Once the configuration is updated and VSCode is reloaded, the JustGoingViral server should connect properly and all tools will be available for testing.

## White-Label Implementation Note:

The filesystem wrapper has been updated to provide actual functionality instead of showing "(wrapper mode)" messages, ensuring a proper white-label experience.
