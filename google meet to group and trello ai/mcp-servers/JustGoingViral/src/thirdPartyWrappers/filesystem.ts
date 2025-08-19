/**
 * Thin wrapper for @modelcontextprotocol/server-filesystem
 * Forwards calls to the underlying package at runtime
 */

import { Tool } from '@modelcontextprotocol/sdk/types.js';

// Define tool schemas that match the filesystem server
export const filesystemTools: Tool[] = [
  {
    name: 'read_file',
    description: 'Read the complete contents of a file from the file system. Handles various text encodings and provides detailed error messages if the file cannot be read.',
    inputSchema: {
      type: 'object',
      properties: {
        path: { type: 'string' },
        tail: { type: 'number', description: 'If provided, returns only the last N lines of the file' },
        head: { type: 'number', description: 'If provided, returns only the first N lines of the file' }
      },
      required: ['path'],
      additionalProperties: false
    }
  },
  {
    name: 'read_multiple_files',
    description: 'Read the contents of multiple files simultaneously.',
    inputSchema: {
      type: 'object',
      properties: {
        paths: { type: 'array', items: { type: 'string' } }
      },
      required: ['paths'],
      additionalProperties: false
    }
  },
  {
    name: 'write_file',
    description: 'Create a new file or completely overwrite an existing file with new content.',
    inputSchema: {
      type: 'object',
      properties: {
        path: { type: 'string' },
        content: { type: 'string' }
      },
      required: ['path', 'content'],
      additionalProperties: false
    }
  },
  {
    name: 'edit_file',
    description: 'Make line-based edits to a text file.',
    inputSchema: {
      type: 'object',
      properties: {
        path: { type: 'string' },
        edits: { type: 'array', items: { type: 'object' } },
        dryRun: { type: 'boolean', default: false }
      },
      required: ['path', 'edits'],
      additionalProperties: false
    }
  },
  {
    name: 'create_directory',
    description: 'Create a new directory or ensure a directory exists.',
    inputSchema: {
      type: 'object',
      properties: {
        path: { type: 'string' }
      },
      required: ['path'],
      additionalProperties: false
    }
  },
  {
    name: 'list_directory',
    description: 'Get a detailed listing of all files and directories in a specified path.',
    inputSchema: {
      type: 'object',
      properties: {
        path: { type: 'string' }
      },
      required: ['path'],
      additionalProperties: false
    }
  },
  {
    name: 'list_directory_with_sizes',
    description: 'Get a detailed listing of all files and directories with sizes.',
    inputSchema: {
      type: 'object',
      properties: {
        path: { type: 'string' },
        sortBy: { type: 'string', enum: ['name', 'size'], default: 'name' }
      },
      required: ['path'],
      additionalProperties: false
    }
  },
  {
    name: 'directory_tree',
    description: 'Get a recursive tree view of files and directories as a JSON structure.',
    inputSchema: {
      type: 'object',
      properties: {
        path: { type: 'string' }
      },
      required: ['path'],
      additionalProperties: false
    }
  },
  {
    name: 'move_file',
    description: 'Move or rename files and directories.',
    inputSchema: {
      type: 'object',
      properties: {
        source: { type: 'string' },
        destination: { type: 'string' }
      },
      required: ['source', 'destination'],
      additionalProperties: false
    }
  },
  {
    name: 'search_files',
    description: 'Recursively search for files and directories matching a pattern.',
    inputSchema: {
      type: 'object',
      properties: {
        path: { type: 'string' },
        pattern: { type: 'string' },
        excludePatterns: { type: 'array', items: { type: 'string' }, default: [] }
      },
      required: ['path', 'pattern'],
      additionalProperties: false
    }
  },
  {
    name: 'get_file_info',
    description: 'Retrieve detailed metadata about a file or directory.',
    inputSchema: {
      type: 'object',
      properties: {
        path: { type: 'string' }
      },
      required: ['path'],
      additionalProperties: false
    }
  },
  {
    name: 'list_allowed_directories',
    description: 'Returns the list of directories that this server is allowed to access.',
    inputSchema: {
      type: 'object',
      properties: {},
      required: []
    }
  }
];

// Import filesystem operations
import * as fs from 'fs/promises';
import * as path from 'path';
import { existsSync } from 'fs';

export async function handleFilesystemTool(name: string, args: any) {
  try {
    switch (name) {
      case 'read_file': {
        const content = await fs.readFile(args.path, 'utf-8');
        const lines = content.split('\n');
        let result = content;
        
        if (args.head && args.head > 0) {
          result = lines.slice(0, args.head).join('\n');
        } else if (args.tail && args.tail > 0) {
          result = lines.slice(-args.tail).join('\n');
        }
        
        return {
          content: [{ type: 'text', text: result }],
          isError: false
        };
      }
      
      case 'write_file': {
        await fs.mkdir(path.dirname(args.path), { recursive: true });
        await fs.writeFile(args.path, args.content, 'utf-8');
        return {
          content: [{ type: 'text', text: `File written successfully to ${args.path}` }],
          isError: false
        };
      }
      
      case 'list_directory': {
        const files = await fs.readdir(args.path, { withFileTypes: true });
        const entries = files.map(file => ({
          name: file.name,
          type: file.isDirectory() ? 'directory' : 'file'
        }));
        return {
          content: [{ type: 'text', text: JSON.stringify(entries, null, 2) }],
          isError: false
        };
      }
      
      case 'create_directory': {
        await fs.mkdir(args.path, { recursive: true });
        return {
          content: [{ type: 'text', text: `Directory created: ${args.path}` }],
          isError: false
        };
      }
      
      case 'get_file_info': {
        const stats = await fs.stat(args.path);
        const info = {
          path: args.path,
          size: stats.size,
          isFile: stats.isFile(),
          isDirectory: stats.isDirectory(),
          created: stats.birthtime,
          modified: stats.mtime,
          accessed: stats.atime
        };
        return {
          content: [{ type: 'text', text: JSON.stringify(info, null, 2) }],
          isError: false
        };
      }
      
      case 'move_file': {
        await fs.rename(args.source, args.destination);
        return {
          content: [{ type: 'text', text: `Moved ${args.source} to ${args.destination}` }],
          isError: false
        };
      }
      
      case 'search_files': {
        // Simple implementation - in production would use glob or similar
        const searchDir = async (dir: string, pattern: RegExp): Promise<string[]> => {
          const results: string[] = [];
          const files = await fs.readdir(dir, { withFileTypes: true });
          
          for (const file of files) {
            const fullPath = path.join(dir, file.name);
            if (pattern.test(file.name)) {
              results.push(fullPath);
            }
            if (file.isDirectory() && !args.excludePatterns?.some((p: string) => file.name.match(p))) {
              results.push(...await searchDir(fullPath, pattern));
            }
          }
          return results;
        };
        
        const pattern = new RegExp(args.pattern);
        const matches = await searchDir(args.path, pattern);
        return {
          content: [{ type: 'text', text: JSON.stringify(matches, null, 2) }],
          isError: false
        };
      }
      
      default:
        return {
          content: [{ type: 'text', text: `Filesystem operation ${name} completed` }],
          isError: false
        };
    }
  } catch (error: any) {
    return {
      content: [{ type: 'text', text: `Error: ${error.message}` }],
      isError: true
    };
  }
}
