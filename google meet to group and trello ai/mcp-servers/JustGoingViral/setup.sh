#!/bin/bash

echo "🚀 Setting up JustGoingViral MCP Server..."
echo ""

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install Node.js and npm first."
    echo "Visit: https://nodejs.org/"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Install ts-node if not already installed
echo "📦 Installing ts-node..."
npm install --save-dev ts-node

# Build the project
echo "🔨 Building the project..."
npm run build

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 Quick Start Guide:"
echo "──────────────────────────────────────────────────────"
echo ""
echo "To add a new MCP server, run:"
echo "  npm run add-mcp-server <repository-url>"
echo ""
echo "Example:"
echo "  npm run add-mcp-server https://github.com/modelcontextprotocol/servers/tree/main/src/weather"
echo ""
echo "After adding a server:"
echo "  1. Add the package to package.json dependencies"
echo "  2. Run: npm install"
echo "  3. Run: npm run build"
echo ""
echo "──────────────────────────────────────────────────────"
echo ""
echo "📚 Full documentation: See README.md"
echo ""
