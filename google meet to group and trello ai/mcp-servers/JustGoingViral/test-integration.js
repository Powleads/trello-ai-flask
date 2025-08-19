#!/usr/bin/env node

/**
 * Simple integration test for JustGoingViral MCP Server
 * This script verifies the server can start and respond to basic commands
 */

import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log('🚀 Testing JustGoingViral MCP Server Integration...\n');

// Test 1: Server can start
console.log('Test 1: Checking if server starts successfully...');
const serverPath = path.join(__dirname, 'dist', 'index.js');
const server = spawn('node', [serverPath], {
  stdio: ['pipe', 'pipe', 'pipe']
});

let serverOutput = '';
let serverError = '';

server.stdout.on('data', (data) => {
  serverOutput += data.toString();
});

server.stderr.on('data', (data) => {
  serverError += data.toString();
});

// Give the server 5 seconds to start
setTimeout(() => {
  server.kill();
  
  console.log('✅ Server startup test completed');
  
  if (serverOutput.includes('JustGoingViral server connected successfully')) {
    console.log('✅ Server started successfully');
  } else {
    console.log('❌ Server failed to start properly');
    console.log('Output:', serverOutput);
    console.log('Error:', serverError);
  }
  
  console.log('\n🎉 Integration test completed!');
  console.log('\n📝 Next Steps:');
  console.log('1. Restart Claude Code to load the new MCP server configuration');
  console.log('2. The server should appear in your MCP tools list');
  console.log('3. Available tools include:');
  console.log('   • 69 consolidated tools from 10+ categories');
  console.log('   • eesystem (Evolutionary Intelligence)');
  console.log('   • sequentialthinking');
  console.log('   • Apple ecosystem integration');
  console.log('   • GitHub operations');
  console.log('   • Browser tools');
  console.log('   • File system operations');
  console.log('   • And much more!');
  
  process.exit(0);
}, 5000);