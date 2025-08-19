/**
 * Thin wrapper for @modelcontextprotocol/server-sequential-thinking
 * Forwards calls to the underlying package at runtime
 */

import { Tool } from '@modelcontextprotocol/sdk/types.js';

// Define tool schemas that match the sequential thinking server
export const sequentialThinkingTools: Tool[] = [
  {
    name: 'sequentialthinking',
    description: `A detailed tool for dynamic and reflective problem-solving through thoughts.
This tool helps analyze problems through a flexible thinking process that can adapt and evolve.
Each thought can build on, question, or revise previous insights as understanding deepens.

When to use this tool:
- Breaking down complex problems into steps
- Planning and design with room for revision
- Analysis that might need course correction
- Problems where the full scope might not be clear initially
- Problems that require a multi-step solution
- Tasks that need to maintain context over multiple steps
- Situations where irrelevant information needs to be filtered out`,
    inputSchema: {
      type: 'object',
      properties: {
        thought: {
          type: 'string',
          description: 'Your current thinking step'
        },
        nextThoughtNeeded: {
          type: 'boolean',
          description: 'Whether another thought step is needed'
        },
        thoughtNumber: {
          type: 'integer',
          description: 'Current thought number',
          minimum: 1
        },
        totalThoughts: {
          type: 'integer',
          description: 'Estimated total thoughts needed',
          minimum: 1
        },
        isRevision: {
          type: 'boolean',
          description: 'Whether this revises previous thinking'
        },
        revisesThought: {
          type: 'integer',
          description: 'Which thought is being reconsidered',
          minimum: 1
        },
        branchFromThought: {
          type: 'integer',
          description: 'Branching point thought number',
          minimum: 1
        },
        branchId: {
          type: 'string',
          description: 'Branch identifier'
        },
        needsMoreThoughts: {
          type: 'boolean',
          description: 'If more thoughts are needed'
        }
      },
      required: ['thought', 'nextThoughtNeeded', 'thoughtNumber', 'totalThoughts']
    }
  }
];

// Handler for sequential thinking tools
export async function handleSequentialThinkingTool(name: string, args: any) {
  try {
    // @ts-ignore - Dynamic import resolved at runtime
    const { createServer } = await import('@modelcontextprotocol/server-sequential-thinking');
    const server = createServer();
    return await server.callTool(name, args);
  } catch (error) {
    console.error(`[Sequential Thinking Wrapper] Error:`, error);
    return {
      content: [{ type: 'text', text: `Sequential thinking tool ${name} failed: ${error}` }],
      isError: true
    };
  }
}
