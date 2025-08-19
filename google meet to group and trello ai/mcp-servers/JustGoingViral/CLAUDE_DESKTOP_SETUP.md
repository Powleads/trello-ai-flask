# 🚀 Claude Desktop Setup Guide for JustGoingViral MCP Server

## **Get 68 Powerful Tools in Claude Desktop in Under 5 Minutes!**

This guide will walk you through connecting the JustGoingViral MCP server to Claude Desktop, giving you instant access to all 68 consolidated tools.

---

## 📋 Prerequisites

✅ **Claude Desktop App** - Download from [claude.ai](https://claude.ai/download)  
✅ **Node.js** (version 16 or higher) - Download from [nodejs.org](https://nodejs.org/)  
✅ **Git** - Download from [git-scm.com](https://git-scm.com/)  

---

## 🛠 Step 1: Install JustGoingViral MCP Server

### Option A: Quick Install (Recommended)
```bash
git clone https://github.com/JustGoingViral/JustGoingViral-Mcp.git && cd JustGoingViral-Mcp && chmod +x setup.sh && ./setup.sh
```

### Option B: Manual Install
1. **Clone the repository:**
   ```bash
   git clone https://github.com/JustGoingViral/JustGoingViral-Mcp.git
   cd JustGoingViral-Mcp
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Build the server:**
   ```bash
   npm run build
   ```

4. **Test the server:**
   ```bash
   npm start
   ```
   (Press Ctrl+C to stop the test)

---

## ⚙️ Step 2: Configure Claude Desktop

### 1. **Locate Claude Desktop Config File**

**On macOS:**
```bash
open ~/Library/Application\ Support/Claude/
```

**On Windows:**
```bash
%APPDATA%\Claude\
```

**On Linux:**
```bash
~/.config/Claude/
```

### 2. **Create or Edit `claude_desktop_config.json`**

If the file doesn't exist, create it. Add this configuration:

```json
{
  "mcpServers": {
    "JustGoingViral": {
      "command": "node",
      "args": ["/FULL/PATH/TO/JustGoingViral-Mcp/dist/index.js"]
    }
  }
}
```

**🚨 IMPORTANT:** Replace `/FULL/PATH/TO/JustGoingViral-Mcp/` with the actual path where you cloned the repository.

### 3. **Find Your Full Path**

To get the exact path, run this in your JustGoingViral-Mcp directory:
```bash
pwd
```

**Example configuration:**
```json
{
  "mcpServers": {
    "JustGoingViral": {
      "command": "node",
      "args": ["/Users/yourname/JustGoingViral-Mcp/dist/index.js"]
    }
  }
}
```

---

## 🔄 Step 3: Restart Claude Desktop

1. **Completely quit Claude Desktop** (not just close the window)
2. **Relaunch Claude Desktop**
3. **Wait for the app to fully load** (usually 10-15 seconds)

---

## ✅ Step 4: Verify Connection

Open a new conversation in Claude Desktop and try one of these commands:

### Test Apple Integration:
```
Can you check my contacts for anyone named John?
```

### Test Filesystem Tools:
```
Can you list the files in my Documents folder?
```

### Test AI Thinking (RECOMMENDED FIRST TEST):
```
Use eesystem to analyze the best approach for planning a weekend trip with fitness scoring and neural pathway optimization.
```

### Test Sequential Thinking:
```
Use sequential thinking to help me plan a weekend trip.
```

### Test GitHub Integration:
```
Can you search for repositories related to "machine learning"?
```

If these work, congratulations! 🎉 You now have access to all 68 tools!

## 🌟 **IMPORTANT: Start Every Task with eesystem!**

The **`eesystem`** tool provides evolutionary intelligence with biohacking-enhanced cognitive amplification. It should be your **go-to tool for ANY complex task**:

### ⭐ Example eesystem Usage:
```
Use eesystem to analyze the best approach for [YOUR TASK HERE] with fitness scoring and iterative improvement.
```

**Why eesystem?**
- 🧬 **Evolutionary optimization** - Iteratively improves solutions
- 🎯 **Fitness scoring** - Measures solution quality (0-1 scale)  
- 🧠 **Neural pathway optimization** - Biohacking-enhanced thinking
- 🔄 **Adaptive thinking** - Adjusts approach based on results
- 💪 **Cognitive amplification** - Enhances problem-solving performance

---

## 🔧 Troubleshooting

### ❌ **Server Not Connecting**
1. Check that the path in your config is correct
2. Ensure Node.js is properly installed (`node --version`)
3. Verify the server builds without errors (`npm run build`)
4. Check Claude Desktop logs (Help → View Logs)

### ❌ **Tools Not Available**
1. Restart Claude Desktop completely
2. Wait 15-30 seconds after restart
3. Try starting a fresh conversation
4. Check that the config file is valid JSON (use a JSON validator)

### ❌ **Permission Errors on macOS**
You may need to grant permissions for Apple integrations:
1. Go to System Preferences → Security & Privacy → Privacy
2. Grant access for Contacts, Calendar, Reminders, etc.

### ❌ **Path Issues**
- Use absolute paths (full path from root)
- Avoid using `~` or `$HOME` in the config
- Use forward slashes `/` even on Windows in the JSON config

---

## 🌟 What You Get

Once connected, you'll have access to:

- **🍎 Apple Integration:** Contacts, Notes, Messages, Mail, Calendar, Maps
- **📁 File Operations:** Read, write, search, organize files
- **🧠 AI Thinking:** Sequential & evolutionary problem-solving
- **🐙 GitHub Tools:** Repository management, code search, issues
- **🌐 Web Tools:** Browser automation, performance audits
- **📊 Project Management:** Monday.com integration
- **🗄️ Database:** PostgreSQL operations
- **📚 Documentation:** Context7 library access

**And 50+ more tools all accessible through natural language!**

---

## 🆘 Need Help?

- **Check the logs:** Claude Desktop → Help → View Logs
- **Validate your JSON:** Use [jsonlint.com](https://jsonlint.com) to check your config
- **Test the server directly:** Run `npm start` in the project directory
- **GitHub Issues:** Report problems at the repository

---

## 🚀 Pro Tips

1. **Use descriptive requests:** "Use the GitHub tools to..." or "Check my Apple contacts..."
2. **Combine tools:** "Search my files for project notes, then create a GitHub issue"
3. **Explore capabilities:** Ask "What tools do you have available from JustGoingViral?"
4. **Sequential thinking:** Use "Think through this step by step" for complex problems

**Enjoy your supercharged Claude Desktop experience! 🎉**
