/**
 * Thin wrapper for @mondaydotcomorg/monday-api-mcp
 * Forwards calls to the underlying package at runtime
 */

import { Tool } from '@modelcontextprotocol/sdk/types.js';

// Define tool schemas that match the monday server
export const mondayTools: Tool[] = [
  {
    name: 'delete_item',
    description: 'Delete an item',
    inputSchema: {
      type: 'object',
      properties: {
        itemId: { type: 'number' }
      },
      required: ['itemId'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'get_board_items_by_name',
    description: 'Get items by board id and term',
    inputSchema: {
      type: 'object',
      properties: {
        boardId: { type: 'number' },
        term: { type: 'string' }
      },
      required: ['boardId', 'term'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'create_item',
    description: 'Create a new item in a monday.com board',
    inputSchema: {
      type: 'object',
      properties: {
        boardId: {
          type: 'number',
          description: 'The id of the board to which the new item will be added'
        },
        name: {
          type: 'string',
          description: 'The name of the new item to be created, must be relevant to the user\'s request'
        },
        groupId: {
          type: 'string',
          description: 'The id of the group id to which the new item will be added, if its not clearly specified, leave empty'
        },
        columnValues: {
          type: 'string',
          description: 'A string containing the new column values for the item following this structure: {\\\"column_id\\\": \\\"value\\\",... you can change multiple columns at once, note that for status column you must use nested value with \'label\' as a key and for date column use \'date\' as key} - example: \"{\\\"text_column_id\\\":\\\"New text\\\", \\\"status_column_id\\\":{\\\"label\\\":\\\"Done\\\"}, \\\"date_column_id\\\":{\\\"date\\\":\\\"2023-05-25\\\"},\\\"dropdown_id\\\":\\\"value\\\", \\\"phone_id\\\":\\\"123-456-7890\\\", \\\"email_id\\\":\\\"test@example.com\\\"}\"'
        }
      },
      required: ['boardId', 'name', 'columnValues'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'create_update',
    description: 'Create a new update in a monday.com board',
    inputSchema: {
      type: 'object',
      properties: {
        itemId: {
          type: 'number',
          description: 'The id of the item to which the update will be added'
        },
        body: {
          type: 'string',
          description: 'The update to be created, must be relevant to the user\'s request'
        }
      },
      required: ['itemId', 'body'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'get_board_schema',
    description: 'Get board schema (columns and groups) by board id',
    inputSchema: {
      type: 'object',
      properties: {
        boardId: {
          type: 'number',
          description: 'The id of the board to get the schema of'
        }
      },
      required: ['boardId'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'get_users_by_name',
    description: 'Get users, can be filtered by name or partial name',
    inputSchema: {
      type: 'object',
      properties: {
        name: {
          type: 'string',
          description: 'The name or partial name of the user to get'
        }
      },
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'change_item_column_values',
    description: 'Change the column values of an item in a monday.com board',
    inputSchema: {
      type: 'object',
      properties: {
        boardId: {
          type: 'number',
          description: 'The ID of the board that contains the item to be updated'
        },
        itemId: {
          type: 'number',
          description: 'The ID of the item to be updated'
        },
        columnValues: {
          type: 'string',
          description: 'A string containing the new column values for the item following this structure: {\\\"column_id\\\": \\\"value\\\",... you can change multiple columns at once, note that for status column you must use nested value with \'label\' as a key and for date column use \'date\' as key} - example: \"{\\\"text_column_id\\\":\\\"New text\\\", \\\"status_column_id\\\":{\\\"label\\\":\\\"Done\\\"}, \\\"date_column_id\\\":{\\\"date\\\":\\\"2023-05-25\\\"}, \\\"phone_id\\\":\\\"123-456-7890\\\", \\\"email_id\\\":\\\"test@example.com\\\"}\"'
        }
      },
      required: ['boardId', 'itemId', 'columnValues'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'move_item_to_group',
    description: 'Move an item to a group in a monday.com board',
    inputSchema: {
      type: 'object',
      properties: {
        itemId: {
          type: 'number',
          description: 'The id of the item to which the update will be added'
        },
        groupId: {
          type: 'string',
          description: 'The id of the group to which the item will be moved'
        }
      },
      required: ['itemId', 'groupId'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'create_board',
    description: 'Create a monday.com board',
    inputSchema: {
      type: 'object',
      properties: {
        boardName: {
          type: 'string',
          description: 'The name of the board to create'
        },
        boardKind: {
          type: 'string',
          enum: ['private', 'public', 'share'],
          default: 'public',
          description: 'The kind of board to create'
        },
        boardDescription: {
          type: 'string',
          description: 'The description of the board to create'
        },
        workspaceId: {
          type: 'string',
          description: 'The ID of the workspace to create the board in'
        }
      },
      required: ['boardName'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'create_column',
    description: 'Create a new column in a monday.com board',
    inputSchema: {
      type: 'object',
      properties: {
        boardId: {
          type: 'number',
          description: 'The id of the board to which the new column will be added'
        },
        columnType: {
          type: 'string',
          enum: [
            'auto_number', 'board_relation', 'button', 'checkbox', 'color_picker', 'country',
            'creation_log', 'date', 'dependency', 'direct_doc', 'doc', 'dropdown', 'email',
            'file', 'formula', 'group', 'hour', 'integration', 'item_assignees', 'item_id',
            'last_updated', 'link', 'location', 'long_text', 'mirror', 'name', 'numbers',
            'people', 'person', 'phone', 'progress', 'rating', 'status', 'subtasks', 'tags',
            'team', 'text', 'time_tracking', 'timeline', 'unsupported', 'vote', 'week', 'world_clock'
          ],
          description: 'The type of the column to be created'
        },
        columnTitle: {
          type: 'string',
          description: 'The title of the column to be created'
        },
        columnDescription: {
          type: 'string',
          description: 'The description of the column to be created'
        },
        columnSettings: {
          type: 'array',
          items: { type: 'string' },
          description: 'The default values for the new column (relevant only for column type \'status\' or \'dropdown\') when possible make the values relevant to the user\'s request'
        }
      },
      required: ['boardId', 'columnType', 'columnTitle'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'all_monday_api',
    description: 'Execute any Monday.com API operation by generating GraphQL queries and mutations dynamically. Make sure you ask only for the fields you need and nothing more. When providing the query/mutation - use get_graphql_schema and get_type_details tools first to understand the schema before crafting your query.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Custom GraphQL query/mutation. you need to provide the full query / mutation'
        },
        variables: {
          type: 'string',
          description: 'JSON string containing the variables for the GraphQL operation'
        }
      },
      required: ['query', 'variables'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  }
];

// Handler for monday tools
export async function handleMondayTool(name: string, args: any) {
  try {
    // @ts-ignore - Dynamic import resolved at runtime
    const { createServer } = await import('@mondaydotcomorg/monday-api-mcp');
    // Create server instance with token from environment
    const server = createServer({ token: process.env.MONDAY_API_TOKEN || '' });
    return await server.callTool(name, args);
  } catch (error) {
    console.error(`[Monday Wrapper] Error:`, error);
    return {
      content: [{ type: 'text', text: `Monday tool ${name} failed: ${error}` }],
      isError: true
    };
  }
}
