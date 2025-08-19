import { describe, it, expect, beforeAll, vi } from 'vitest';

const stubResult = (label: string) => ({
  content: [{ type: 'text', text: label }],
  isError: false,
});

vi.mock('../src/thirdPartyWrappers/github.js', () => ({
  githubTools: [],
  handleGitHubTool: vi.fn(async (name: string) => stubResult(`github:${name}`)),
}));

vi.mock('../src/thirdPartyWrappers/justGoingViral.js', () => ({
  justGoingViralTools: [],
  handleJustGoingViralTool: vi.fn(async (name: string) => stubResult(`apple:${name}`)),
}));

vi.mock('../src/thirdPartyWrappers/memory.js', () => ({
  memoryTools: [],
  handleMemoryTool: vi.fn(async (name: string) => stubResult(`memory:${name}`)),
}));

vi.mock('../src/thirdPartyWrappers/postgres.js', () => ({
  postgresTools: [],
  handlePostgresTool: vi.fn(async (name: string) => stubResult(`postgres:${name}`)),
}));

vi.mock('../src/thirdPartyWrappers/sequentialThinking.js', () => ({
  sequentialThinkingTools: [],
  handleSequentialThinkingTool: vi.fn(async (name: string) => stubResult(`seq:${name}`)),
}));

vi.mock('../src/thirdPartyWrappers/context7.js', () => ({
  context7Tools: [],
  handleContext7Tool: vi.fn(async (name: string) => stubResult(`context7:${name}`)),
}));

vi.mock('../src/thirdPartyWrappers/browserTools.js', () => ({
  browserToolsTools: [],
  handleBrowserToolsTool: vi.fn(async (name: string) => stubResult(`browser:${name}`)),
}));

vi.mock('../src/thirdPartyWrappers/monday.js', () => ({
  mondayTools: [],
  handleMondayTool: vi.fn(async (name: string) => stubResult(`monday:${name}`)),
}));

vi.mock('../src/thirdPartyWrappers/modelcontextprotocolServerMemory.js', () => ({
  modelcontextprotocolServerMemoryTools: [],
  handleModelcontextprotocolServerMemoryTool: vi.fn(async (name: string) => stubResult(`modelmemory:${name}`)),
}));

vi.mock('../src/thirdPartyWrappers/modelcontextprotocolServerFilesystem.js', () => ({
  modelcontextprotocolServerFilesystemTools: [],
  handleModelcontextprotocolServerFilesystemTool: vi.fn(async (name: string) => stubResult(`modelfs:${name}`)),
}));

vi.mock('../src/thirdPartyWrappers/evolutionaryIntelligence.js', () => ({
  evolutionaryIntelligenceTools: [],
  handleEvolutionaryIntelligenceTool: vi.fn(async (name: string) => stubResult(`evo:${name}`)),
}));

vi.mock('../src/thirdPartyWrappers/serverHealth.js', () => ({
  serverHealthTools: [],
  handleServerHealthTool: vi.fn(async (name: string) => stubResult(`health:${name}`)),
}));

let callToolHandler: any;

beforeAll(async () => {
  process.env.NODE_ENV = 'test';
  const mod = await import('../src/index.js');
  const server = (mod as any).server;
  callToolHandler = (server as any)._requestHandlers.get('tools/call');
});

async function callTool(name: string, args: any) {
  return await callToolHandler({ method: 'tools/call', params: { name, arguments: args } });
}

describe('Filesystem wrapper', () => {
  it('reads a file', async () => {
    const result = await callTool('read_file', { path: 'package.json' });
    expect(result.isError).toBe(false);
    expect(result.content[0].text).toContain('JustGoingViral');
  });
});

describe('GitHub wrapper', () => {
  it('calls GitHub tool', async () => {
    const result = await callTool('search_repositories', { query: 'test' });
    expect(result.isError).toBe(false);
    expect(result.content[0].text).toBe('github:search_repositories');
  });
});

describe('Apple wrapper', () => {
  it('calls Apple tool', async () => {
    const result = await callTool('notes', { operation: 'list' });
    expect(result.isError).toBe(false);
    expect(result.content[0].text).toBe('apple:notes');
  });
});
