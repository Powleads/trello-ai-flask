import { Tool } from '@modelcontextprotocol/sdk/types.js';
import os from 'os';

export const serverHealthTools: Tool[] = [
  {
    name: 'server_health',
    description: 'Returns current server health metrics like uptime, memory usage and load averages',
    inputSchema: {
      type: 'object',
      properties: {},
      required: [],
      additionalProperties: false
    }
  }
];

export async function handleServerHealthTool(name: string, _args: any) {
  const uptimeSeconds = process.uptime();
  const memory = process.memoryUsage();
  const load = os.loadavg();
  const info = {
    uptimeSeconds,
    memory,
    loadAverage1m: load[0],
    loadAverage5m: load[1],
    loadAverage15m: load[2]
  };
  return {
    content: [{ type: 'text', text: JSON.stringify(info, null, 2) }],
    isError: false
  };
}
