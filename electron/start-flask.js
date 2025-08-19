/**
 * Flask server startup helper for Electron
 * This module handles starting the Python Flask server
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

class FlaskManager {
  constructor() {
    this.flaskProcess = null;
    this.isRunning = false;
    this.port = 5000;
  }

  /**
   * Find Python executable
   */
  findPython() {
    const possiblePythonPaths = [
      'python3',
      'python',
      'C:\\Python39\\python.exe',
      'C:\\Python310\\python.exe',
      'C:\\Python311\\python.exe',
      'C:\\Users\\' + process.env.USERNAME + '\\AppData\\Local\\Programs\\Python\\Python39\\python.exe',
      'C:\\Users\\' + process.env.USERNAME + '\\AppData\\Local\\Programs\\Python\\Python310\\python.exe',
      'C:\\Users\\' + process.env.USERNAME + '\\AppData\\Local\\Programs\\Python\\Python311\\python.exe'
    ];

    for (const pythonPath of possiblePythonPaths) {
      try {
        const result = spawn.sync(pythonPath, ['--version']);
        if (result.status === 0) {
          console.log(`Found Python at: ${pythonPath}`);
          return pythonPath;
        }
      } catch (e) {
        // Continue to next path
      }
    }
    
    throw new Error('Python not found. Please install Python 3.x');
  }

  /**
   * Start the Flask server
   */
  start(appPath, port = 5000) {
    return new Promise((resolve, reject) => {
      if (this.isRunning) {
        resolve();
        return;
      }

      this.port = port;
      const pythonPath = this.findPython();
      
      // Use electron_wrapper.py if it exists, otherwise use web_app.py
      const scriptFile = fs.existsSync(path.join(appPath, 'electron_wrapper.py')) 
        ? 'electron_wrapper.py' 
        : 'web_app.py';
      
      console.log(`Starting Flask server with ${scriptFile}...`);
      
      this.flaskProcess = spawn(pythonPath, [scriptFile], {
        cwd: appPath,
        env: {
          ...process.env,
          FLASK_PORT: port.toString(),
          ELECTRON_ENV: 'development'
        }
      });

      this.flaskProcess.stdout.on('data', (data) => {
        const output = data.toString();
        console.log(`Flask: ${output}`);
        
        if (output.includes('Running on') || output.includes('started on')) {
          this.isRunning = true;
          setTimeout(() => resolve(), 2000); // Give Flask time to fully initialize
        }
      });

      this.flaskProcess.stderr.on('data', (data) => {
        const error = data.toString();
        console.error(`Flask Error: ${error}`);
        
        // Check if it's just a warning
        if (!error.includes('WARNING') && !error.includes('Info:')) {
          // Don't reject on warnings
        }
      });

      this.flaskProcess.on('error', (error) => {
        console.error('Failed to start Flask server:', error);
        this.isRunning = false;
        reject(error);
      });

      this.flaskProcess.on('close', (code) => {
        console.log(`Flask server exited with code ${code}`);
        this.isRunning = false;
      });

      // Timeout after 30 seconds
      setTimeout(() => {
        if (!this.isRunning) {
          reject(new Error('Flask server failed to start within 30 seconds'));
        }
      }, 30000);
    });
  }

  /**
   * Stop the Flask server
   */
  stop() {
    if (this.flaskProcess) {
      console.log('Stopping Flask server...');
      
      // Try graceful shutdown first
      if (process.platform === 'win32') {
        spawn('taskkill', ['/pid', this.flaskProcess.pid, '/f', '/t']);
      } else {
        this.flaskProcess.kill('SIGTERM');
      }
      
      this.flaskProcess = null;
      this.isRunning = false;
    }
  }

  /**
   * Restart the Flask server
   */
  async restart(appPath, port) {
    this.stop();
    await new Promise(resolve => setTimeout(resolve, 1000)); // Wait a bit
    return this.start(appPath, port);
  }

  /**
   * Check if Flask server is responding
   */
  async checkHealth() {
    try {
      const fetch = (await import('node-fetch')).default;
      const response = await fetch(`http://localhost:${this.port}/desktop/status`);
      return response.ok;
    } catch (error) {
      return false;
    }
  }
}

module.exports = FlaskManager;