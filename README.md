# 🤖 macOS AI Agent

> **Voice-controlled, fully autonomous macOS automation using local AI models**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![macOS](https://img.shields.io/badge/Platform-macOS-lightgrey.svg)]()
[![Ollama](https://img.shields.io/badge/AI-Ollama-purple.svg)](https://ollama.ai)

## What Is This?

A voice-controlled AI agent that can operate your Mac. Talk to it, and it will:

- **See** your screen using vision AI (LLaVA)
- **Plan** complex multi-step tasks (Llama 3.2)
- **Execute** actions: click, type, open apps, navigate
- **Verify** results and replan if needed
- **Ask** clarifying questions when uncertain

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                            │
│    🎤 Voice Input ←→ 🤖 CLI Interface ←→ 🔊 Voice Output         │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                               │
│  Task Understanding → Planning → Execution → Verification         │
│                    └── Replanning if failed ──┘                   │
└─────────┬────────────────┬────────────────┬──────────────────────┘
          ▼                ▼                ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│     PLANNER     │ │   PERCEPTION    │ │    EXECUTOR     │
│  Llama 3.2 3B   │ │   LLaVA 7B      │ │   PyAutoGUI     │
│                 │ │                 │ │                 │
│ • Task breakdown│ │ • Screenshots   │ │ • Mouse control │
│ • Step planning │ │ • Screen read   │ │ • Keyboard      │
│ • Clarification │ │ • Element find  │ │ • System cmds   │
│ • Suggestions   │ │ • Verification  │ │ • App control   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Quick Start

### 1. Install Ollama & Models

```bash
# Install Ollama
brew install ollama

# Start Ollama service
ollama serve

# Pull required models (in another terminal)
ollama pull llama3.2:3b    # Planning model
ollama pull llava:7b       # Vision model
```

### 2. Setup Agent

```bash
# Clone and enter directory
cd "os agent"

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Grant accessibility permissions (required for mouse/keyboard control)
# System Preferences → Privacy & Security → Accessibility → Add Terminal
```

### 3. Run

```bash
# 🖥️ GUI Mode (Recommended)
python gui.py

# Interactive CLI mode
python run_agent.py

# Voice-controlled mode
python run_agent.py --voice

# Execute single task
python run_agent.py --task "open Safari and go to google.com"
```

## GUI Features

The modern GUI provides:

- **Task Input** - Type or speak your commands
- **Voice Button** - Click 🎤 to use voice input
- **Quick Actions** - One-click system controls
- **Activity Log** - See what the agent is doing
- **Progress Tracking** - Visual step completion
- **Status Indicator** - Know when agent is ready/busy

![GUI Screenshot](screenshots/gui.png)

## Usage Examples

### Direct System Commands
These execute immediately without vision:

```
"Turn on WiFi"
"Turn off Bluetooth"  
"Set volume to 50%"
"Mute"
"Enable dark mode"
"Open Chrome"
"Go to youtube.com"
```

### Vision-Based Tasks
These use the screen to find elements:

```
"Click on the Safari icon in the dock"
"Find the search box and type hello"
"Click the red close button"
"Scroll down"
```

### Multi-Step Tasks
Automatically broken into steps:

```
"Open WhatsApp and send hi to John"
→ Step 1: Open WhatsApp
→ Step 2: Find John in chat list
→ Step 3: Click on John's chat
→ Step 4: Find message input
→ Step 5: Type "hi"
→ Step 6: Press Enter to send

"Search for Python tutorials on YouTube"
→ Step 1: Open Safari
→ Step 2: Go to youtube.com
→ Step 3: Find search box
→ Step 4: Type "Python tutorials"
→ Step 5: Press Enter
```

## Project Structure

```
os-agent/
├── gui.py                 # 🖥️ Modern GUI interface
├── run_agent.py           # CLI entry point
├── requirements.txt       # Dependencies
├── README.md              # Documentation
└── agent/
    ├── core/
    │   ├── config.py         # Configuration & system commands
    │   ├── models.py         # Data models (Action, Plan, Step)
    │   └── orchestrator.py   # Main workflow coordinator
    ├── perception/
    │   ├── screenshot.py     # Screen capture
    │   └── vision.py         # LLaVA vision analysis
    ├── planner/
    │   ├── llm_client.py     # Ollama API wrapper
    │   └── task_planner.py   # Task → Steps breakdown
    ├── executor/
    │   ├── system.py         # System commands (wifi, volume, etc)
    │   ├── input_control.py  # Mouse & keyboard via PyAutoGUI
    │   └── action_executor.py # Action dispatcher
    ├── voice/
    │   └── interface.py      # Speech recognition & TTS
    └── utils/
        └── logging.py        # Logging utilities
```

## Available System Commands

| Command | What it does |
|---------|--------------|
| `wifi_on` / `wifi_off` | Toggle WiFi |
| `bluetooth_on` / `bluetooth_off` | Toggle Bluetooth |
| `volume_up` / `volume_down` | Adjust volume |
| `volume_set` | Set specific volume (0-100) |
| `mute` / `unmute` | Mute/unmute audio |
| `brightness_up` / `brightness_down` | Adjust brightness |
| `dark_mode_on` / `dark_mode_off` | Toggle dark mode |
| `sleep` / `lock` | Sleep display or lock |
| `screenshot` | Take screenshot |
| `open_app` | Open application |
| `close_app` | Close application |
| `open_url` | Open URL in browser |

## How It Works

1. **Voice/Text Input** → User gives a command
2. **Orchestrator** → Coordinates the workflow
3. **Planner** → Breaks task into executable steps
4. **Perception** → Analyzes screen to find targets
5. **Executor** → Performs actions (click, type, etc)
6. **Verification** → Checks if action succeeded
7. **Replanning** → If failed, tries alternative approach

### Example Flow: "Send a message in Slack"

```
1. User: "Send hi to John in Slack"

2. Planner thinks:
   - Need to open Slack
   - Need to find John's chat
   - Need to type and send message
   
3. Creates plan:
   Step 1: Open Slack app
   Step 2: Find John in sidebar (requires vision)
   Step 3: Click John's chat
   Step 4: Type "hi" in message box
   Step 5: Press Enter to send

4. Executes step by step:
   - Takes screenshot after each action
   - Verifies expected result
   - Replans if something fails
```

## Requirements

- **macOS** (tested on Ventura/Sonoma)
- **Python 3.11+**
- **Ollama** with models:
  - `llama3.2:3b` - Planning
  - `llava:7b` - Vision
- **Accessibility permissions** for Terminal/Python

## Troubleshooting

### "Ollama not running"
```bash
ollama serve
```

### "Permission denied" for mouse/keyboard
1. Open System Preferences
2. Privacy & Security → Accessibility
3. Add Terminal (or your terminal app)
4. Restart terminal

### Voice not working
```bash
pip install SpeechRecognition pyaudio edge-tts
```

### Models not found
```bash
ollama pull llama3.2:3b
ollama pull llava:7b
```

## Limitations

- **macOS only** - Uses macOS-specific commands
- **Best effort** - Vision may miss elements
- **Local AI** - Quality depends on model capability
- **No web automation** - Basic browser control only

## License

MIT License - Use freely, no warranty.
