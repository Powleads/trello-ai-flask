import { execSync } from 'child_process';
import fs from 'fs-extra';
import path, { dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const main = async () => {
  const repoUrl = process.argv[2];
  if (!repoUrl) {
    console.error('Please provide a git repository URL.');
    process.exit(1);
  }

  console.log(`Adding MCP server from ${repoUrl}...`);

  // 1. Clone the repository into a temporary directory
  const tempDir = path.join(__dirname, 'temp-mcp-server');
  if (fs.existsSync(tempDir)) {
    fs.removeSync(tempDir);
  }
  fs.mkdirSync(tempDir, { recursive: true });

  let serverPath = tempDir;
  // Check if the URL is a subdirectory
  if (repoUrl.includes('/tree/main/')) {
    const [repo, dir] = repoUrl.split('/tree/main/');
    const repoPath = `${repo}.git`;
    execSync(`cd ${tempDir} && git init && git remote add -f origin ${repoPath} && git config core.sparseCheckout true && echo "${dir}" >> .git/info/sparse-checkout && git pull origin main`);
    serverPath = path.join(tempDir, dir);
  } else {
    execSync(`git clone ${repoUrl} ${tempDir}`);
  }

  // 2. Read the package.json to get the server name
  let packageJsonPath = path.join(serverPath, 'package.json');
  if (!fs.existsSync(packageJsonPath)) {
    packageJsonPath = path.join(tempDir, 'package.json');
    if (!fs.existsSync(packageJsonPath)) {
      console.error('The repository does not contain a package.json file in the root or subdirectory.');
      fs.removeSync(tempDir);
      process.exit(1);
    }
    // If package.json is in the root, the server path is the temp dir
    serverPath = tempDir;
  }
  const packageJson = fs.readJsonSync(packageJsonPath);
  const serverName = packageJson.name;
  if (!serverName) {
    console.error('The package.json does not have a name.');
    fs.removeSync(tempDir);
    process.exit(1);
  }

  const camelCaseServerName = serverName.replace(/@/g, '').replace(/\//g, '-').replace(/-(\w)/g, (g) => g[1].toUpperCase());


  // 3. Generate the wrapper file
  const wrapperTemplate = `
/**
 * Thin wrapper for ${serverName}
 * Forwards calls to the underlying package at runtime
 */

import { Tool } from '@modelcontextprotocol/sdk/types.js';

// Define tool schemas that match the ${serverName} server
export const ${camelCaseServerName}Tools: Tool[] = [
  // TODO: Add tool schemas here
];

// Handler for ${serverName} tools
export async function handle${camelCaseServerName.charAt(0).toUpperCase() + camelCaseServerName.slice(1)}Tool(name: string, args: any) {
  try {
    // @ts-ignore - Dynamic import resolved at runtime
    const { createServer } = await import('${serverName}');
    const server = createServer();
    return await server.callTool(name, args);
  } catch (error) {
    console.error(\`[${serverName} Wrapper] Error:\`, error);
    return {
      content: [{ type: 'text', text: \`${serverName} tool \${name} failed: \${error}\` }],
      isError: true
    };
  }
}
`;

  const wrapperPath = path.join(__dirname, `../src/thirdPartyWrappers/${camelCaseServerName}.ts`);
  fs.writeFileSync(wrapperPath, wrapperTemplate.trim());

  // 4. Populate the tool schemas
  const toolsFilePath = path.join(serverPath, 'src/tools.ts');
  if (fs.existsSync(toolsFilePath)) {
    const toolsFileContent = fs.readFileSync(toolsFilePath, 'utf-8');
    const toolDefinitions = toolsFileContent.match(/const \w+?: Tool = {[\s\S]*?};/g);
    if (toolDefinitions) {
      const wrapperFileContent = fs.readFileSync(wrapperPath, 'utf-8');
      const newContent = wrapperFileContent.replace('// TODO: Add tool schemas here', toolDefinitions.join('\n\n'));
      fs.writeFileSync(wrapperPath, newContent);
    }
  }

  // 5. Update the main tools.ts file
  const mainToolsPath = path.join(__dirname, '../src/tools.ts');
  let mainToolsContent = fs.readFileSync(mainToolsPath, 'utf-8');
  mainToolsContent = mainToolsContent.replace(
    'const tools = [',
    `import { ${camelCaseServerName}Tools } from './thirdPartyWrappers/${camelCaseServerName}.js';\n\nconst tools = [\n  ...${camelCaseServerName}Tools,`
  );
  fs.writeFileSync(mainToolsPath, mainToolsContent);

  // 6. Update the main index.ts file
  const mainIndexPath = path.join(__dirname, '../src/index.ts');
  let mainIndexContent = fs.readFileSync(mainIndexPath, 'utf-8');
  mainIndexContent = mainIndexContent.replace(
    'import { handleMondayTool } from "./thirdPartyWrappers/monday.js";',
    `import { handleMondayTool } from "./thirdPartyWrappers/monday.js";\nimport { handle${camelCaseServerName.charAt(0).toUpperCase() + camelCaseServerName.slice(1)}Tool } from "./thirdPartyWrappers/${camelCaseServerName}.js";`
  );
  mainIndexContent = mainIndexContent.replace(
    '// Route Monday.com tools',
    `// Route ${serverName} tools
    const ${camelCaseServerName}ToolNames = [
      // TODO: Add tool names here
    ];

    if (${camelCaseServerName}ToolNames.includes(name)) {
      return await handle${camelCaseServerName.charAt(0).toUpperCase() + camelCaseServerName.slice(1)}Tool(name, args);
    }

    // Route Monday.com tools`
  );
  fs.writeFileSync(mainIndexPath, mainIndexContent);

  // 7. Populate the tool names in index.ts
  if (fs.existsSync(toolsFilePath)) {
    const toolsFileContent = fs.readFileSync(toolsFilePath, 'utf-8');
    const toolNames = (toolsFileContent.match(/name: "(\w+)"/g) || []).map(match => match.replace(/name: "(\w+)"/, '$1'));
    if (toolNames.length > 0) {
      let mainIndexContent = fs.readFileSync(mainIndexPath, 'utf-8');
      mainIndexContent = mainIndexContent.replace(
        '// TODO: Add tool names here',
        `'${toolNames.join("', '")}'`
      );
      fs.writeFileSync(mainIndexPath, mainIndexContent);
    }
  }


  // Clean up the temporary directory
  fs.removeSync(tempDir);

  console.log('MCP server added successfully!');
};

main().catch((error) => {
  console.error('Failed to add MCP server:', error);
  process.exit(1);
});
