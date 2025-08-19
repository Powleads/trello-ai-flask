# 🚀 Quick Start for the Next Developer

## One-Line Setup Command

Share this single command with the next developer:

```bash
git clone https://github.com/JustGoingViral/JustGoingViral-Mcpo.git && cd JustGoingViral-Mcpo && chmod +x setup.sh && ./setup.sh
```

## What This Does

1. **Clones the repository**
2. **Sets up the entire project** (installs dependencies, builds)
3. **Shows instructions** for adding new MCP servers

## Adding a New MCP Server

After setup, they can add any MCP server with:

```bash
npm run add-mcp-server <repository-url>
```

### Examples:
```bash
# Add a weather server
npm run add-mcp-server https://github.com/modelcontextprotocol/servers/tree/main/src/weather

# Add a Slack server
npm run add-mcp-server https://github.com/modelcontextprotocol/servers/tree/main/src/slack
```

## What Happens Automatically

The automation script will:
- Clone the MCP server
- Generate all wrapper files
- Update all imports
- Configure routing
- Extract tool definitions

## Manual Steps After Adding

1. Add package to `package.json`
2. Run `npm install`
3. Run `npm run build`

That's it! The complex integration work is automated.

## Already Included Servers

- Apple MCP (contacts, notes, messages, mail, calendar, maps, web search)
- Filesystem operations
- Memory/Knowledge graph
- GitHub integration
- PostgreSQL
- Sequential thinking
- Context7 documentation
- Browser tools
- Monday.com integration
- **Your JustGoingViral MCP server**

---

**Share this file or the one-line command above with the next developer!**
