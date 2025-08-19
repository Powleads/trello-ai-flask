/**
 * Thin wrapper for @agentdeskai/browser-tools-mcp
 * Forwards calls to the underlying package at runtime
 */

import { Tool } from '@modelcontextprotocol/sdk/types.js';

// Define tool schemas that match the browser tools server
export const browserToolsTools: Tool[] = [
  {
    name: 'getConsoleLogs',
    description: 'Check our browser logs',
    inputSchema: {
      type: 'object'
    }
  },
  {
    name: 'getConsoleErrors',
    description: 'Check our browsers console errors',
    inputSchema: {
      type: 'object'
    }
  },
  {
    name: 'getNetworkErrors',
    description: 'Check our network ERROR logs',
    inputSchema: {
      type: 'object'
    }
  },
  {
    name: 'getNetworkLogs',
    description: 'Check ALL our network logs',
    inputSchema: {
      type: 'object'
    }
  },
  {
    name: 'takeScreenshot',
    description: 'Take a screenshot of the current browser tab',
    inputSchema: {
      type: 'object'
    }
  },
  {
    name: 'getSelectedElement',
    description: 'Get the selected element from the browser',
    inputSchema: {
      type: 'object'
    }
  },
  {
    name: 'wipeLogs',
    description: 'Wipe all browser logs from memory',
    inputSchema: {
      type: 'object'
    }
  },
  {
    name: 'runAccessibilityAudit',
    description: 'Run an accessibility audit on the current page',
    inputSchema: {
      type: 'object',
      properties: {},
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'runPerformanceAudit',
    description: 'Run a performance audit on the current page',
    inputSchema: {
      type: 'object',
      properties: {},
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'runSEOAudit',
    description: 'Run an SEO audit on the current page',
    inputSchema: {
      type: 'object',
      properties: {},
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'runNextJSAudit',
    description: 'Run a Next.js specific audit',
    inputSchema: {
      type: 'object',
      properties: {},
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'runDebuggerMode',
    description: 'Run debugger mode to debug an issue in our application',
    inputSchema: {
      type: 'object'
    }
  },
  {
    name: 'runAuditMode',
    description: 'Run audit mode to optimize our application for SEO, accessibility and performance',
    inputSchema: {
      type: 'object'
    }
  },
  {
    name: 'runBestPracticesAudit',
    description: 'Run a best practices audit on the current page',
    inputSchema: {
      type: 'object',
      properties: {},
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  }
];

// Handler for browser tools
export async function handleBrowserToolsTool(name: string, args: any) {
  try {
    // @ts-ignore - Dynamic import resolved at runtime
    const { createServer } = await import('@agentdeskai/browser-tools-mcp');
    const server = createServer();
    return await server.callTool(name, args);
  } catch (error) {
    console.error(`[Browser Tools Wrapper] Error:`, error);
    return {
      content: [{ type: 'text', text: `Browser tools ${name} failed: ${error}` }],
      isError: true
    };
  }
}
