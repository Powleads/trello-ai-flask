/**
 * Thin wrapper for @modelcontextprotocol/server-postgres
 * Forwards calls to the underlying package at runtime
 */

import { Tool } from '@modelcontextprotocol/sdk/types.js';

// Define tool schemas that match the postgres server
export const postgresTools: Tool[] = [
  {
    name: 'query',
    description: 'Run a read-only SQL query',
    inputSchema: {
      type: 'object',
      properties: {
        sql: { type: 'string' }
      }
    }
  }
];

// Handler for postgres tools
export async function handlePostgresTool(name: string, args: any) {
  try {
    // @ts-ignore - Dynamic import resolved at runtime
    const { createServer } = await import('@modelcontextprotocol/server-postgres');
    // Create server instance with connection string from environment
    const server = createServer(process.env.POSTGRES_CONNECTION_STRING || '');
    return await server.callTool(name, args);
  } catch (error) {
    console.error(`[Postgres Wrapper] Error:`, error);
    return {
      content: [{ type: 'text', text: `Postgres tool ${name} failed: ${error}` }],
      isError: true
    };
  }
}
