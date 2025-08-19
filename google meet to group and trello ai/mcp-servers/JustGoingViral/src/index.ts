#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { runAppleScript } from "run-applescript";
import tools from "./tools.js";
import { handleFilesystemTool } from "./thirdPartyWrappers/filesystem.js";
import { handleMemoryTool } from "./thirdPartyWrappers/memory.js";
import { handleGitHubTool } from "./thirdPartyWrappers/github.js";
import { handlePostgresTool } from "./thirdPartyWrappers/postgres.js";
import { handleSequentialThinkingTool } from "./thirdPartyWrappers/sequentialThinking.js";
import { handleContext7Tool } from "./thirdPartyWrappers/context7.js";
import { handleBrowserToolsTool } from "./thirdPartyWrappers/browserTools.js";
import { handleMondayTool } from "./thirdPartyWrappers/monday.js";
import { handleModelcontextprotocolServerMemoryTool } from "./thirdPartyWrappers/modelcontextprotocolServerMemory.js";
import { handleModelcontextprotocolServerFilesystemTool } from "./thirdPartyWrappers/modelcontextprotocolServerFilesystem.js";
import { handleEvolutionaryIntelligenceTool } from "./thirdPartyWrappers/evolutionaryIntelligence.js";
import { handleJustGoingViralTool } from "./thirdPartyWrappers/justGoingViral.js";
import { handleServerHealthTool } from "./thirdPartyWrappers/serverHealth.js";

console.error("Starting JustGoingViral consolidated MCP server...");

// Lazy loading of Apple MCP modules
let contacts: typeof import('./utils/contacts.js').default | null = null;
let notes: typeof import('./utils/notes.js').default | null = null;
let message: typeof import('./utils/message.js').default | null = null;
let mail: typeof import('./utils/mail.js').default | null = null;
let reminders: typeof import('./utils/reminders.js').default | null = null;
let webSearch: typeof import('./utils/webSearch.js').default | null = null;
let calendar: typeof import('./utils/calendar.js').default | null = null;
let maps: typeof import('./utils/maps.js').default | null = null;

// Helper function for lazy module loading
async function loadAppleModule<T extends 'contacts' | 'notes' | 'message' | 'mail' | 'reminders' | 'webSearch' | 'calendar' | 'maps'>(moduleName: T): Promise<any> {
  try {
    switch (moduleName) {
      case 'contacts':
        if (!contacts) contacts = (await import('./utils/contacts.js')).default;
        return contacts;
      case 'notes':
        if (!notes) notes = (await import('./utils/notes.js')).default;
        return notes;
      case 'message':
        if (!message) message = (await import('./utils/message.js')).default;
        return message;
      case 'mail':
        if (!mail) mail = (await import('./utils/mail.js')).default;
        return mail;
      case 'reminders':
        if (!reminders) reminders = (await import('./utils/reminders.js')).default;
        return reminders;
      case 'webSearch':
        if (!webSearch) webSearch = (await import('./utils/webSearch.js')).default;
        return webSearch;
      case 'calendar':
        if (!calendar) calendar = (await import('./utils/calendar.js')).default;
        return calendar;
      case 'maps':
        if (!maps) maps = (await import('./utils/maps.js')).default;
        return maps;
      default:
        throw new Error(`Unknown module: ${moduleName}`);
    }
  } catch (e) {
    console.error(`Error loading module ${moduleName}:`, e);
    throw e;
  }
}

// Main server initialization
const server = new Server(
  {
    name: "JustGoingViral",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  try {
    const { name, arguments: args } = request.params;

    if (!args) {
      throw new Error("No arguments provided");
    }

    // Route filesystem tools to their wrapper
    const filesystemToolNames = [
      'read_file', 'read_multiple_files', 'write_file', 'edit_file', 
      'create_directory', 'list_directory', 'list_directory_with_sizes',
      'directory_tree', 'move_file', 'search_files', 'get_file_info', 'list_allowed_directories'
    ];
    
    if (filesystemToolNames.includes(name)) {
      return await handleFilesystemTool(name, args);
    }

    // Route memory tools
    const memoryToolNames = [
      'create_entities', 'create_relations', 'add_observations', 'delete_entities',
      'delete_observations', 'delete_relations', 'read_graph', 'search_nodes', 'open_nodes'
    ];
    
    if (memoryToolNames.includes(name)) {
      return await handleMemoryTool(name, args);
    }

    // Route GitHub tools
    const githubToolNames = [
      'create_or_update_file', 'search_repositories', 'create_repository', 'get_file_contents',
      'push_files', 'create_issue', 'create_pull_request', 'list_issues', 'search_code'
    ];
    
    if (githubToolNames.includes(name)) {
      return await handleGitHubTool(name, args);
    }

    // Route Postgres tools
    if (name === 'query') {
      return await handlePostgresTool(name, args);
    }

    // Route Sequential Thinking tools
    if (name === 'sequentialthinking') {
      return await handleSequentialThinkingTool(name, args);
    }

    // Route Context7 tools
    if (name === 'resolve-library-id' || name === 'get-library-docs') {
      return await handleContext7Tool(name, args);
    }

    // Route Browser Tools
    const browserToolNames = [
      'getConsoleLogs', 'getConsoleErrors', 'getNetworkErrors', 'getNetworkLogs',
      'takeScreenshot', 'getSelectedElement', 'wipeLogs', 'runAccessibilityAudit',
      'runPerformanceAudit', 'runSEOAudit', 'runNextJSAudit', 'runDebuggerMode',
      'runAuditMode', 'runBestPracticesAudit'
    ];
    
    if (browserToolNames.includes(name)) {
      return await handleBrowserToolsTool(name, args);
    }

    // Route @modelcontextprotocol/server-filesystem tools
    const modelcontextprotocolServerFilesystemToolNames = [
      'read_file',
      'read_multiple_files',
      'write_file',
      'edit_file',
      'create_directory',
      'list_directory',
      'list_directory_with_sizes',
      'directory_tree',
      'move_file',
      'search_files',
      'get_file_info',
      'list_allowed_directories'
    ];

    if (modelcontextprotocolServerFilesystemToolNames.includes(name)) {
      return await handleModelcontextprotocolServerFilesystemTool(name, args);
    }

    // Route @modelcontextprotocol/server-memory tools
    const modelcontextprotocolServerMemoryToolNames = [
      'create_entities',
      'create_relations',
      'add_observations',
      'delete_entities',
      'delete_observations',
      'delete_relations',
      'read_graph',
      'search_nodes',
      'open_nodes'
    ];

    if (modelcontextprotocolServerMemoryToolNames.includes(name)) {
      return await handleModelcontextprotocolServerMemoryTool(name, args);
    }

    // Route Monday.com tools
    const mondayToolNames = [
      'delete_item', 'get_board_items_by_name', 'create_item', 'create_update',
      'get_board_schema', 'get_users_by_name', 'change_item_column_values',
      'move_item_to_group', 'create_board', 'create_column', 'all_monday_api'
    ];
    
    if (mondayToolNames.includes(name)) {
      return await handleMondayTool(name, args);
    }

    // Route server health tool
    if (name === 'server_health') {
      return await handleServerHealthTool(name, args);
    }

    // Route Evolutionary Intelligence tools
    if (name === 'eesystem') {
      return await handleEvolutionaryIntelligenceTool(name, args);
    }

    // Route JustGoingViral tools
    const justGoingViralToolNames = [
      'contacts', 'notes', 'messages', 'mail', 'reminders', 'webSearch', 'calendar', 'maps'
    ];

    if (justGoingViralToolNames.includes(name)) {
      return await handleJustGoingViralTool(name, args);
    }

    // Handle Apple MCP tools (simplified version - focusing on key tools)
    switch (name) {
      case "contacts": {
        const contactsModule = await loadAppleModule('contacts');
        if (args.name) {
          const numbers = await contactsModule.findNumber(args.name);
          return {
            content: [{
              type: "text",
              text: numbers.length ?
                `${args.name}: ${numbers.join(", ")}` :
                `No contact found for "${args.name}"`
            }],
            isError: false
          };
        } else {
          const allNumbers = await contactsModule.getAllNumbers();
          const formattedContacts = Object.entries(allNumbers)
            .filter(([_, phones]) => (phones as string[]).length > 0)
            .map(([name, phones]) => `${name}: ${(phones as string[]).join(", ")}`);
          return {
            content: [{
              type: "text",
              text: formattedContacts.length > 0 ?
                `Found contacts:\n\n${formattedContacts.join("\n")}` :
                "No contacts with phone numbers found."
            }],
            isError: false
          };
        }
      }

      case "notes": {
        const notesModule = await loadAppleModule('notes');
        if (args.operation === 'search') {
          const results = await notesModule.searchNotes(args.searchText);
          return {
            content: [{
              type: "text",
              text: results.length > 0 ?
                `Found ${results.length} notes matching "${args.searchText}":\n\n${results.join("\n\n")}` :
                `No notes found matching "${args.searchText}".`
            }],
            isError: false
          };
        } else if (args.operation === 'list') {
          const allNotes = await notesModule.listNotes();
          return {
            content: [{
              type: "text",
              text: allNotes.length > 0 ?
                `Found ${allNotes.length} notes:\n\n${allNotes.join("\n\n")}` :
                "No notes found."
            }],
            isError: false
          };
        } else if (args.operation === 'create') {
          await notesModule.createNote(args.title, args.body, args.folderName);
          return {
            content: [{
              type: "text",
              text: `Note created successfully: "${args.title}"`
            }],
            isError: false
          };
        }
        break;
      }

      case "messages": {
        const messageModule = await loadAppleModule('message');
        if (args.operation === 'send') {
          await messageModule.sendMessage(args.phoneNumber, args.message);
          return {
            content: [{
              type: "text",
              text: `Message sent to ${args.phoneNumber}`
            }],
            isError: false
          };
        } else if (args.operation === 'read') {
          const messages = await messageModule.readMessages(args.phoneNumber, args.limit);
          return {
            content: [{
              type: "text",
              text: messages.length > 0 ?
                `Messages with ${args.phoneNumber}:\n\n${messages.join("\n\n")}` :
                `No messages found with ${args.phoneNumber}.`
            }],
            isError: false
          };
        }
        // Add other message operations as needed
        break;
      }

      case "mail": {
        const mailModule = await loadAppleModule('mail');
        if (args.operation === 'unread') {
          const unreadMails = await mailModule.getUnreadEmails(args.account, args.mailbox, args.limit);
          return {
            content: [{
              type: "text",
              text: unreadMails.length > 0 ?
                `Found ${unreadMails.length} unread emails:\n\n${unreadMails.join("\n\n")}` :
                "No unread emails found."
            }],
            isError: false
          };
        } else if (args.operation === 'send') {
          await mailModule.sendEmail(args.to, args.subject, args.body, args.cc, args.bcc);
          return {
            content: [{
              type: "text",
              text: `Email sent to ${args.to}`
            }],
            isError: false
          };
        }
        // Add other mail operations as needed
        break;
      }

      case "webSearch": {
        const webSearchModule = await loadAppleModule('webSearch');
        const result = await webSearchModule.webSearch(args.query);
        return {
          content: [{
            type: "text",
            text: result.results.length > 0 ?
              `Found ${result.results.length} results for "${args.query}". ${result.results.map((r: any) => `[${r.displayUrl}] ${r.title} - ${r.snippet}`).join("\n")}` :
              `No results found for "${args.query}".`
          }],
          isError: false
        };
      }

      case "calendar": {
        const calendarModule = await loadAppleModule('calendar');
        if (args.operation === 'search') {
          const events = await calendarModule.searchEvents(args.searchText, args.fromDate, args.toDate, args.limit);
          return {
            content: [{
              type: "text",
              text: events.length > 0 ?
                `Found ${events.length} events:\n\n${events.join("\n\n")}` :
                "No events found."
            }],
            isError: false
          };
        } else if (args.operation === 'create') {
          await calendarModule.createEvent(args.title, args.startDate, args.endDate, args.location, args.notes, args.isAllDay, args.calendarName);
          return {
            content: [{
              type: "text",
              text: `Event created: "${args.title}"`
            }],
            isError: false
          };
        }
        // Add other calendar operations as needed
        break;
      }

      case "reminders": {
        const remindersModule = await loadAppleModule('reminders');
        if (args.operation === 'create') {
          await remindersModule.createReminder(args.name, args.listName, args.notes, args.dueDate);
          return {
            content: [{
              type: "text",
              text: `Reminder created: "${args.name}"`
            }],
            isError: false
          };
        }
        // Add other reminder operations as needed
        break;
      }

      case "maps": {
        const mapsModule = await loadAppleModule('maps');
        if (args.operation === 'search') {
          const locations = await mapsModule.searchLocations(args.query, args.limit);
          return {
            content: [{
              type: "text",
              text: locations.length > 0 ?
                `Found ${locations.length} locations:\n\n${locations.join("\n\n")}` :
                `No locations found for "${args.query}".`
            }],
            isError: false
          };
        }
        // Add other maps operations as needed
        break;
      }

      default:
        return {
          content: [{ type: "text", text: `Tool "${name}" not yet implemented in JustGoingViral` }],
          isError: true,
        };
    }
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Error: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
      isError: true,
    };
  }
});

// Start the server
async function main() {
  try {
    console.error("Initializing transport...");
    const transport = new StdioServerTransport();
    
    console.error("Connecting transport to server...");
    await server.connect(transport);
    console.error("JustGoingViral server connected successfully!");
  } catch (error) {
    console.error("Failed to initialize JustGoingViral server:", error);
    process.exit(1);
  }
}

if (process.env.NODE_ENV !== "test") {
  main();
}

export { server };
