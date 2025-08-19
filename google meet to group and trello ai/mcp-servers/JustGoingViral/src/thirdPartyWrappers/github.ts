/**
 * Thin wrapper for @modelcontextprotocol/server-github
 * Forwards calls to the underlying package at runtime
 */

import { Tool } from '@modelcontextprotocol/sdk/types.js';

// Define tool schemas that match the GitHub server
export const githubTools: Tool[] = [
  {
    name: 'create_or_update_file',
    description: 'Create or update a single file in a GitHub repository',
    inputSchema: {
      type: 'object',
      properties: {
        owner: { type: 'string', description: 'Repository owner (username or organization)' },
        repo: { type: 'string', description: 'Repository name' },
        path: { type: 'string', description: 'Path where to create/update the file' },
        content: { type: 'string', description: 'Content of the file' },
        message: { type: 'string', description: 'Commit message' },
        branch: { type: 'string', description: 'Branch to create/update the file in' },
        sha: { type: 'string', description: 'SHA of the file being replaced (required when updating existing files)' }
      },
      required: ['owner', 'repo', 'path', 'content', 'message', 'branch'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'search_repositories',
    description: 'Search for GitHub repositories',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Search query (see GitHub search syntax)' },
        page: { type: 'number', description: 'Page number for pagination (default: 1)' },
        perPage: { type: 'number', description: 'Number of results per page (default: 30, max: 100)' }
      },
      required: ['query'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'create_repository',
    description: 'Create a new GitHub repository in your account',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Repository name' },
        description: { type: 'string', description: 'Repository description' },
        private: { type: 'boolean', description: 'Whether the repository should be private' },
        autoInit: { type: 'boolean', description: 'Initialize with README.md' }
      },
      required: ['name'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'get_file_contents',
    description: 'Get the contents of a file or directory from a GitHub repository',
    inputSchema: {
      type: 'object',
      properties: {
        owner: { type: 'string', description: 'Repository owner (username or organization)' },
        repo: { type: 'string', description: 'Repository name' },
        path: { type: 'string', description: 'Path to the file or directory' },
        branch: { type: 'string', description: 'Branch to get contents from' }
      },
      required: ['owner', 'repo', 'path'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'push_files',
    description: 'Push multiple files to a GitHub repository in a single commit',
    inputSchema: {
      type: 'object',
      properties: {
        owner: { type: 'string', description: 'Repository owner (username or organization)' },
        repo: { type: 'string', description: 'Repository name' },
        branch: { type: 'string', description: 'Branch to push to (e.g., \'main\' or \'master\')' },
        files: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              path: { type: 'string' },
              content: { type: 'string' }
            },
            required: ['path', 'content'],
            additionalProperties: false
          },
          description: 'Array of files to push'
        },
        message: { type: 'string', description: 'Commit message' }
      },
      required: ['owner', 'repo', 'branch', 'files', 'message'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'create_issue',
    description: 'Create a new issue in a GitHub repository',
    inputSchema: {
      type: 'object',
      properties: {
        owner: { type: 'string' },
        repo: { type: 'string' },
        title: { type: 'string' },
        body: { type: 'string' },
        assignees: { type: 'array', items: { type: 'string' } },
        milestone: { type: 'number' },
        labels: { type: 'array', items: { type: 'string' } }
      },
      required: ['owner', 'repo', 'title'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'create_pull_request',
    description: 'Create a new pull request in a GitHub repository',
    inputSchema: {
      type: 'object',
      properties: {
        owner: { type: 'string', description: 'Repository owner (username or organization)' },
        repo: { type: 'string', description: 'Repository name' },
        title: { type: 'string', description: 'Pull request title' },
        body: { type: 'string', description: 'Pull request body/description' },
        head: { type: 'string', description: 'The name of the branch where your changes are implemented' },
        base: { type: 'string', description: 'The name of the branch you want the changes pulled into' },
        draft: { type: 'boolean', description: 'Whether to create the pull request as a draft' },
        maintainer_can_modify: { type: 'boolean', description: 'Whether maintainers can modify the pull request' }
      },
      required: ['owner', 'repo', 'title', 'head', 'base'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  // Adding more essential GitHub tools
  {
    name: 'list_issues',
    description: 'List issues in a GitHub repository with filtering options',
    inputSchema: {
      type: 'object',
      properties: {
        owner: { type: 'string' },
        repo: { type: 'string' },
        direction: { type: 'string', enum: ['asc', 'desc'] },
        labels: { type: 'array', items: { type: 'string' } },
        page: { type: 'number' },
        per_page: { type: 'number' },
        since: { type: 'string' },
        sort: { type: 'string', enum: ['created', 'updated', 'comments'] },
        state: { type: 'string', enum: ['open', 'closed', 'all'] }
      },
      required: ['owner', 'repo'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  },
  {
    name: 'search_code',
    description: 'Search for code across GitHub repositories',
    inputSchema: {
      type: 'object',
      properties: {
        q: { type: 'string' },
        order: { type: 'string', enum: ['asc', 'desc'] },
        page: { type: 'number', minimum: 1 },
        per_page: { type: 'number', minimum: 1, maximum: 100 }
      },
      required: ['q'],
      additionalProperties: false,
      $schema: 'http://json-schema.org/draft-07/schema#'
    }
  }
];

// Handler for GitHub tools
export async function handleGitHubTool(name: string, args: any) {
  try {
    // @ts-ignore - Dynamic import resolved at runtime
    const { createServer } = await import('@modelcontextprotocol/server-github');
    const server = createServer();
    return await server.callTool(name, args);
  } catch (error) {
    console.error(`[GitHub Wrapper] Error:`, error);
    return {
      content: [{ type: 'text', text: `GitHub tool ${name} failed: ${error}` }],
      isError: true
    };
  }
}
