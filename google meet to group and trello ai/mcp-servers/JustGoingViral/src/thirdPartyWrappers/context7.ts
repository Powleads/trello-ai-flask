/**
 * Thin wrapper for @upstash/context7-mcp
 * Forwards calls to the underlying package at runtime
 */

import { Tool } from '@modelcontextprotocol/sdk/types.js';

// Define tool schemas that match the context7 server
export const context7Tools: Tool[] = [
  {
    name: 'resolve-library-id',
    description: `Resolves a package/product name to a Context7-compatible library ID and returns a list of matching libraries.

You MUST call this function before 'get-library-docs' to obtain a valid Context7-compatible library ID UNLESS the user explicitly provides a library ID in the format '/org/project' or '/org/project/version' in their query.

Selection Process:
1. Analyze the query to understand what library/package the user is looking for
2. Return the most relevant match based on:
- Name similarity to the query (exact matches prioritized)
- Description relevance to the query's intent
- Documentation coverage (prioritize libraries with higher Code Snippet counts)
- Trust score (consider libraries with scores of 7-10 more authoritative)

Response Format:
- Return the selected library ID in a clearly marked section
- Provide a brief explanation for why this library was chosen
- If multiple good matches exist, acknowledge this but proceed with the most relevant one
- If no good matches exist, clearly state this and suggest query refinements

For ambiguous queries, request clarification before proceeding with a best-guess match.`,
    inputSchema: {
      type: 'object',
      properties: {
        libraryName: {
          type: 'string',
          description: 'Library name to search for and retrieve a Context7-compatible library ID.'
        }
      },
      required: ['libraryName'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'get-library-docs',
    description: `Fetches up-to-date documentation for a library. You must call 'resolve-library-id' first to obtain the exact Context7-compatible library ID required to use this tool, UNLESS the user explicitly provides a library ID in the format '/org/project' or '/org/project/version' in their query.`,
    inputSchema: {
      type: 'object',
      properties: {
        context7CompatibleLibraryID: {
          type: 'string',
          description: `Exact Context7-compatible library ID (e.g., '/mongodb/docs', '/vercel/next.js', '/supabase/supabase', '/vercel/next.js/v14.3.0-canary.87') retrieved from 'resolve-library-id' or directly from user query in the format '/org/project' or '/org/project/version'.`
        },
        topic: {
          type: 'string',
          description: `Topic to focus documentation on (e.g., 'hooks', 'routing').`
        },
        tokens: {
          type: 'number',
          description: 'Maximum number of tokens of documentation to retrieve (default: 10000). Higher values provide more context but consume more tokens.'
        }
      },
      required: ['context7CompatibleLibraryID'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  }
];

// Handler for context7 tools
export async function handleContext7Tool(name: string, args: any) {
  try {
    // @ts-ignore - Dynamic import resolved at runtime
    const { createServer } = await import('@upstash/context7-mcp');
    const server = createServer();
    return await server.callTool(name, args);
  } catch (error) {
    console.error(`[Context7 Wrapper] Error:`, error);
    return {
      content: [{ type: 'text', text: `Context7 tool ${name} failed: ${error}` }],
      isError: true
    };
  }
}
