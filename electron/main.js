const { app, BrowserWindow, Menu, Tray, ipcMain, dialog, Notification, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const Store = require('electron-store');

// Initialize electron store for settings
const store = new Store();

let mainWindow;
let tray;
let flaskProcess;
let isQuitting = false;

// Flask server configuration
const FLASK_PORT = store.get('flaskPort', 5000);
const FLASK_HOST = 'localhost';
const FLASK_URL = `http://${FLASK_HOST}:${FLASK_PORT}`;

// Function to check if Flask server is running
async function checkFlaskServer() {
  try {
    const fetch = (await import('node-fetch')).default;
    const response = await fetch(FLASK_URL);
    return response.ok || response.status === 404; // Flask is running even if 404
  } catch (error) {
    return false;
  }
}

// Function to start Flask server
function startFlaskServer() {
  return new Promise((resolve, reject) => {
    console.log('Starting Flask server...');
    
    // Get the path to the Flask app
    const flaskAppPath = app.isPackaged 
      ? path.join(process.resourcesPath, 'app')
      : path.join(__dirname, '..', 'google meet to group and trello ai');
    
    // Check if Python is available
    const pythonCommand = 'python';
    
    // Start the Flask process - use web_app.py directly
    flaskProcess = spawn(pythonCommand, ['web_app.py'], {
      cwd: flaskAppPath,
      env: { ...process.env, FLASK_PORT: FLASK_PORT.toString() },
      shell: true
    });

    flaskProcess.stdout.on('data', (data) => {
      console.log(`Flask: ${data}`);
      if (data.toString().includes('Running on') || data.toString().includes('Serving Flask app')) {
        setTimeout(() => resolve(), 2000); // Give Flask time to fully start
      }
    });

    flaskProcess.stderr.on('data', (data) => {
      console.error(`Flask Error: ${data}`);
      // Check if Flask actually started (it outputs to stderr sometimes)
      if (data.toString().includes('Running on')) {
        setTimeout(() => resolve(), 2000);
      }
    });

    flaskProcess.on('error', (error) => {
      console.error('Failed to start Flask server:', error);
      reject(error);
    });

    flaskProcess.on('close', (code) => {
      console.log(`Flask server exited with code ${code}`);
      if (!isQuitting) {
        // Restart Flask if it crashes
        setTimeout(() => startFlaskServer(), 5000);
      }
    });

    // Timeout if Flask doesn't start
    setTimeout(() => {
      reject(new Error('Flask server failed to start in time'));
    }, 30000);
  });
}

// Function to stop Flask server
function stopFlaskServer() {
  if (flaskProcess) {
    console.log('Stopping Flask server...');
    flaskProcess.kill('SIGTERM');
    flaskProcess = null;
  }
}

// Create the main application window
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, 'icons', 'icon.png'),
    show: false,
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default'
  });

  // Load the Flask app
  mainWindow.loadURL(FLASK_URL);

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Handle window close
  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
      
      // Show notification
      new Notification({
        title: 'Trello AI Desktop',
        body: 'Application minimized to system tray'
      }).show();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Open external links in browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

// Create system tray
function createTray() {
  const iconPath = path.join(__dirname, 'icons', 'tray.png');
  tray = new Tray(iconPath);
  
  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show App',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        } else {
          createWindow();
        }
      }
    },
    {
      label: 'Settings',
      click: () => {
        // Open settings window
        openSettingsWindow();
      }
    },
    { type: 'separator' },
    {
      label: 'Restart Flask Server',
      click: async () => {
        stopFlaskServer();
        await startFlaskServer();
        if (mainWindow) {
          mainWindow.reload();
        }
      }
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray.setToolTip('Trello AI Desktop');
  tray.setContextMenu(contextMenu);

  // Double click to show window
  tray.on('double-click', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    } else {
      createWindow();
    }
  });
}

// Create settings window
function openSettingsWindow() {
  const settingsWindow = new BrowserWindow({
    width: 600,
    height: 400,
    parent: mainWindow,
    modal: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  settingsWindow.loadFile(path.join(__dirname, 'settings.html'));
}

// App event handlers
app.whenReady().then(async () => {
  try {
    // Start Flask server
    await startFlaskServer();
    
    // Wait for Flask to be ready
    let retries = 0;
    while (!await checkFlaskServer() && retries < 10) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      retries++;
    }

    // Even if Flask check fails, try to continue (Flask might be running but not responding to root)
    if (retries >= 10) {
      console.warn('Flask server check timed out, but continuing anyway...');
    }

    // Create window and tray
    createWindow();
    createTray();

    // Create application menu
    const template = [
      {
        label: 'File',
        submenu: [
          {
            label: 'New Meeting',
            accelerator: 'CmdOrCtrl+N',
            click: () => {
              mainWindow.webContents.executeJavaScript('window.location.href = "/google-meet"');
            }
          },
          {
            label: 'View Trello Boards',
            accelerator: 'CmdOrCtrl+B',
            click: () => {
              mainWindow.webContents.executeJavaScript('window.location.href = "/dashboard"');
            }
          },
          { type: 'separator' },
          {
            label: 'Settings',
            accelerator: 'CmdOrCtrl+,',
            click: () => openSettingsWindow()
          },
          { type: 'separator' },
          {
            label: 'Quit',
            accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
            click: () => {
              isQuitting = true;
              app.quit();
            }
          }
        ]
      },
      {
        label: 'Edit',
        submenu: [
          { role: 'undo' },
          { role: 'redo' },
          { type: 'separator' },
          { role: 'cut' },
          { role: 'copy' },
          { role: 'paste' },
          { role: 'selectAll' }
        ]
      },
      {
        label: 'View',
        submenu: [
          { role: 'reload' },
          { role: 'forceReload' },
          { role: 'toggleDevTools' },
          { type: 'separator' },
          { role: 'resetZoom' },
          { role: 'zoomIn' },
          { role: 'zoomOut' },
          { type: 'separator' },
          { role: 'togglefullscreen' }
        ]
      },
      {
        label: 'Help',
        submenu: [
          {
            label: 'Documentation',
            click: () => {
              shell.openExternal('https://github.com/yourusername/trello-ai-desktop');
            }
          },
          {
            label: 'Report Issue',
            click: () => {
              shell.openExternal('https://github.com/yourusername/trello-ai-desktop/issues');
            }
          },
          { type: 'separator' },
          {
            label: 'About',
            click: () => {
              dialog.showMessageBox(mainWindow, {
                type: 'info',
                title: 'About Trello AI Desktop',
                message: 'Trello AI Desktop',
                detail: 'Version 1.0.0\n\nA powerful desktop application for managing Trello boards with AI-powered Google Meet integration.',
                buttons: ['OK']
              });
            }
          }
        ]
      }
    ];

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);

  } catch (error) {
    console.error('Failed to start application:', error);
    dialog.showErrorBox('Startup Error', `Failed to start application: ${error.message}`);
    app.quit();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

app.on('before-quit', () => {
  isQuitting = true;
  stopFlaskServer();
});

// IPC handlers
ipcMain.handle('get-app-version', () => {
  return app.getVersion();
});

ipcMain.handle('get-settings', () => {
  return store.store;
});

ipcMain.handle('save-settings', (event, settings) => {
  Object.keys(settings).forEach(key => {
    store.set(key, settings[key]);
  });
  return true;
});

ipcMain.handle('show-notification', (event, { title, body }) => {
  new Notification({ title, body }).show();
});

// Export for testing
module.exports = { startFlaskServer, stopFlaskServer };