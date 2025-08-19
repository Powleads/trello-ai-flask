const { app, BrowserWindow, Menu, Tray, ipcMain, dialog, Notification, shell } = require('electron');
const path = require('path');
const Store = require('electron-store');

// Initialize electron store for settings
const store = new Store();

let mainWindow;
let tray;
let isQuitting = false;

// Flask server configuration - assume it's already running
const FLASK_PORT = store.get('flaskPort', 5000);
const FLASK_HOST = 'localhost';
const FLASK_URL = `http://${FLASK_HOST}:${FLASK_PORT}`;

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
  
  // Create a default icon if it doesn't exist
  if (!require('fs').existsSync(iconPath)) {
    console.log('Tray icon not found, skipping tray creation');
    return;
  }
  
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
        openSettingsWindow();
      }
    },
    { type: 'separator' },
    {
      label: 'Reload',
      click: () => {
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
  console.log('Starting Electron app (Flask already running)...');
  
  // Create window and tray directly since Flask is already running
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