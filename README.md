# fd File Search Tool

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

## Overview

A simple and fast GUI wrapper for the `fd` command, providing intuitive file search with a modern interface using ttkbootstrap. Supports fuzzy search, search history, and various options.

## Features

- 🚀 **Fast Search**: High-speed file/directory search using `fd` command
- 🎨 **Modern UI**: Beautiful themed interface with ttkbootstrap
- 🔍 **Fuzzy Filtering**: Real-time fuzzy filtering of results
- 📁 **File Operations**: Open files/folders, context menu for explorer and path copy
- 💾 **History**: Save/load search results
- ⚙️ **Rich Options**: File type, hidden files, case sensitivity, etc.
- 🎭 **Themes**: Multiple selectable themes
- 💡 **Auto Save**: Auto-save and restore settings

## Screenshot

![Main Screen](screenshot.png)

## Requirements

- Python 3.12 or later
- `fd` command (must be installed separately)

## Dependencies

- `ttkbootstrap>=1.13.10`
- `cx-freeze>=8.3.0` (for building executables)

## Installation

### 1. Install fd Command

#### Windows

```bash
choco install fd
scoop install fd
# Or download from https://github.com/sharkdp/fd/releases
```

#### macOS

```bash
brew install fd
```

#### Linux

```bash
sudo apt install fd-find  # Ubuntu/Debian
sudo pacman -S fd         # Arch Linux
# Or use your package manager or download from GitHub
```

### 2. Set Up Application

```bash
git clone https://github.com/yourusername/tk-fd-search.git
cd tk-fd-search
pip install -r requirements.txt
python main.py
```

## Build Executable

```bash
python setup.py build
# Built files will be in the build/ folder
```

## Usage

1. **Specify Search Folder**: Select the target folder using the "Browse" button
2. **Enter Keyword**: Input the file/folder name you want to search
3. **Set Options**: File type, include hidden files, case sensitivity
4. **Start Search**: Click "Start Search" or press Enter
5. **Operate on Results**: Double-click to open, right-click for context menu (open in explorer, copy path), use the filter field for fuzzy search

### History Feature

- **Save**: Menu "History" → "Save Current Results"
- **Load**: Menu "History" → "Open History File"

### Theme Switching

Select your preferred theme from the "Theme" menu. Settings are saved automatically.

## File Structure

```
tk-fd-search/
├── main.py              # Main application
├── setup.py             # cx_Freeze build settings
├── pyproject.toml       # Project settings
├── requirements.txt     # Dependencies
├── icon/
│   └── icon.ico         # Application icon
├── fd.exe               # fd command (Windows)
├── history/             # Search history folder (auto-generated)
└── settings.json        # Settings file (auto-generated)
```

## Development

```bash
pip install -e .
python main.py
```

## Build and Test

```bash
python setup.py build
./build/exe.win-amd64-3.12/fd\ File Search Tool.exe
```

## Contribution

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to your branch (`git push origin feature/amazing-feature`)
5. Create a pull request

## License

This project is licensed under the MIT License. See the [LICENSE-MIT](LICENSE-MIT) file for details.

## Author

**dekunocode**

## Acknowledgments

- [fd](https://github.com/sharkdp/fd) - Fast file search tool
- [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap) - Modern Tkinter themes
- [cx_Freeze](https://github.com/marcelotduarte/cx_Freeze) - Packaging Python apps as executables

## Support

Please use [Issues](https://github.com/yourusername/tk-fd-search/issues) for bug reports and feature requests.
