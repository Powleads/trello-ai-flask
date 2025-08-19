# Trello AI Desktop Application

A powerful Electron-based desktop application that wraps the Trello AI web app with Google Meet integration.

## Features

- 🖥️ **Native Desktop Experience**: Full desktop application with system tray integration
- 🔔 **Desktop Notifications**: Get notified about important events
- 📁 **File Drag & Drop**: Easily upload files by dragging them into the app
- ⚙️ **Settings Management**: Configure app behavior through a native settings window
- 🔄 **Auto-start Flask Server**: Automatically manages the Python backend
- 🎨 **Modern UI**: Clean, responsive interface optimized for desktop use

## Prerequisites

1. **Node.js** (v14 or higher): Download from [nodejs.org](https://nodejs.org/)
2. **Python** (v3.8 or higher): Download from [python.org](https://python.org/)
3. **Git**: For cloning the repository

## Installation

### 1. Install Python Dependencies

```bash
cd "google meet to group and trello ai"
pip install -r requirements.txt
cd ..
```

### 2. Install Node Dependencies

```bash
npm install
```

## Running the Application

### Easy Method (Windows)

Double-click the `start-electron.bat` file or run:

```bash
start-electron.bat
```

### Manual Method

```bash
npm start
```

## Building for Distribution

### Windows

```bash
npm run build
```

This will create an installer in the `dist` folder.

### macOS

```bash
npm run build
```

### Linux

```bash
npm run build
```

## Project Structure

```
TRELLO AI/
├── electron/              # Electron application files
│   ├── main.js           # Main process
│   ├── preload.js        # Preload script for security
│   ├── settings.html     # Settings window
│   ├── start-flask.js    # Flask server manager
│   └── icons/            # Application icons
├── google meet to group and trello ai/  # Flask backend
│   ├── web_app.py        # Main Flask application
│   ├── electron_wrapper.py # Electron-specific Flask wrapper
│   └── ...               # Other Python modules
├── package.json          # Node.js dependencies
├── start-electron.bat    # Windows startup script
└── README_ELECTRON.md    # This file
```

## Configuration

The app stores its configuration in:
- **Windows**: `%APPDATA%/trello-ai-desktop`
- **macOS**: `~/Library/Application Support/trello-ai-desktop`
- **Linux**: `~/.config/trello-ai-desktop`

### Available Settings

- **Flask Server Port**: Configure the port for the Flask backend
- **Theme**: Light, Dark, or Auto (follows system)
- **Auto-start**: Start with Windows/macOS/Linux
- **Start Minimized**: Start in system tray
- **Notifications**: Enable/disable desktop notifications
- **Auto-refresh**: Set refresh interval for data updates

## Troubleshooting

### Flask Server Won't Start

1. Ensure Python is installed and in PATH
2. Check that all Python dependencies are installed
3. Verify no other application is using port 5000
4. Check the console for error messages

### Electron App Won't Launch

1. Run `npm install` to ensure all dependencies are installed
2. Check Node.js version (must be v14+)
3. Delete `node_modules` and reinstall

### Icons Not Showing

Place appropriate icon files in the `electron/icons/` directory:
- `icon.png` (512x512px)
- `icon.ico` (Windows)
- `icon.icns` (macOS)
- `tray.png` (16x16 or 24x24px)

## Development

### Running in Development Mode

1. Start Flask server manually:
```bash
cd "google meet to group and trello ai"
python web_app.py
```

2. In another terminal, start Electron:
```bash
npm start
```

### Debug Mode

Press `Ctrl+Shift+D` in the app to open Developer Tools.

## Security Considerations

- The Flask server only listens on localhost for security
- Context isolation is enabled in Electron
- Node integration is disabled in renderer process
- All external links open in the default browser

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details

## Support

For issues or questions:
- Create an issue on GitHub
- Check existing issues for solutions
- Consult the Flask app documentation

## Credits

- Built with [Electron](https://www.electronjs.org/)
- Backend powered by [Flask](https://flask.palletsprojects.com/)
- Trello integration via [py-trello](https://github.com/sarumont/py-trello)