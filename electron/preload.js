const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // App information
  getVersion: () => ipcRenderer.invoke('get-app-version'),
  
  // Settings
  getSettings: () => ipcRenderer.invoke('get-settings'),
  saveSettings: (settings) => ipcRenderer.invoke('save-settings', settings),
  
  // Notifications
  showNotification: (options) => ipcRenderer.invoke('show-notification', options),
  
  // Window controls
  minimizeWindow: () => ipcRenderer.send('minimize-window'),
  maximizeWindow: () => ipcRenderer.send('maximize-window'),
  closeWindow: () => ipcRenderer.send('close-window'),
  
  // Flask server management
  restartFlaskServer: () => ipcRenderer.send('restart-flask-server'),
  
  // File operations
  selectFile: () => ipcRenderer.invoke('select-file'),
  selectDirectory: () => ipcRenderer.invoke('select-directory'),
  
  // External links
  openExternal: (url) => ipcRenderer.send('open-external', url),
  
  // Event listeners
  onUpdateAvailable: (callback) => {
    ipcRenderer.on('update-available', callback);
  },
  
  onFlaskServerStatus: (callback) => {
    ipcRenderer.on('flask-server-status', callback);
  }
});

// Add custom styles for desktop app
window.addEventListener('DOMContentLoaded', () => {
  // Add desktop-specific CSS
  const style = document.createElement('style');
  style.textContent = `
    /* Desktop-specific styles */
    body {
      user-select: none;
      -webkit-app-region: drag;
    }
    
    input, textarea, button, a, select {
      -webkit-app-region: no-drag;
      user-select: auto;
    }
    
    /* Custom scrollbar for desktop */
    ::-webkit-scrollbar {
      width: 10px;
      height: 10px;
    }
    
    ::-webkit-scrollbar-track {
      background: #f1f1f1;
    }
    
    ::-webkit-scrollbar-thumb {
      background: #888;
      border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
      background: #555;
    }
    
    /* Add desktop notification badge */
    .desktop-indicator {
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: #4CAF50;
      color: white;
      padding: 10px 20px;
      border-radius: 5px;
      font-size: 12px;
      z-index: 9999;
      display: none;
    }
    
    .desktop-indicator.show {
      display: block;
    }
  `;
  document.head.appendChild(style);
  
  // Add desktop indicator
  const indicator = document.createElement('div');
  indicator.className = 'desktop-indicator';
  indicator.textContent = 'Desktop Mode';
  document.body.appendChild(indicator);
  
  // Show indicator briefly
  setTimeout(() => {
    indicator.classList.add('show');
    setTimeout(() => {
      indicator.classList.remove('show');
    }, 3000);
  }, 1000);
  
  // Enhance existing functionality with desktop features
  enhanceForDesktop();
});

function enhanceForDesktop() {
  // Add keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + R to reload (prevent default browser reload)
    if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
      e.preventDefault();
      window.location.reload();
    }
    
    // Ctrl/Cmd + Shift + D to toggle dev tools
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'D') {
      e.preventDefault();
      ipcRenderer.send('toggle-dev-tools');
    }
  });
  
  // Intercept form submissions to add desktop notifications
  const originalFetch = window.fetch;
  window.fetch = async function(...args) {
    const response = await originalFetch.apply(this, args);
    
    // Check for successful Trello operations
    if (response.ok && args[0].includes('/api/')) {
      const url = args[0];
      
      if (url.includes('/create-card')) {
        window.electronAPI.showNotification({
          title: 'Trello Card Created',
          body: 'New card has been successfully created!'
        });
      } else if (url.includes('/process-transcript')) {
        window.electronAPI.showNotification({
          title: 'Transcript Processed',
          body: 'Meeting transcript has been analyzed!'
        });
      }
    }
    
    return response;
  };
  
  // Add file drag and drop support
  document.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.stopPropagation();
  });
  
  document.addEventListener('drop', (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      // Handle dropped files
      handleDroppedFiles(files);
    }
  });
}

function handleDroppedFiles(files) {
  // Check if we're on a page that accepts file uploads
  const fileInput = document.querySelector('input[type="file"]');
  const textArea = document.querySelector('textarea[name="transcript"]');
  
  if (fileInput) {
    // Simulate file selection
    const dataTransfer = new DataTransfer();
    for (let file of files) {
      dataTransfer.items.add(file);
    }
    fileInput.files = dataTransfer.files;
    
    // Trigger change event
    const event = new Event('change', { bubbles: true });
    fileInput.dispatchEvent(event);
  } else if (textArea && files[0].type.includes('text')) {
    // Read text file and paste into transcript field
    const reader = new FileReader();
    reader.onload = (e) => {
      textArea.value = e.target.result;
      
      // Trigger input event
      const event = new Event('input', { bubbles: true });
      textArea.dispatchEvent(event);
    };
    reader.readAsText(files[0]);
  }
}