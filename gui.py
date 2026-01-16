"""
macOS AI Agent - Professional GUI
Clean, modern white theme with full NLP integration via Ollama
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import asyncio
import queue
import time
import json
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass


# ═══════════════════════════════════════════════════════════════════════════════
# THEME & STYLING
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Theme:
    """Professional Light Theme"""
    # Backgrounds
    bg_primary: str = "#FFFFFF"
    bg_secondary: str = "#F8F9FA"
    bg_tertiary: str = "#E9ECEF"
    bg_card: str = "#FFFFFF"
    
    # Text
    text_primary: str = "#212529"
    text_secondary: str = "#6C757D"
    text_muted: str = "#ADB5BD"
    
    # Accents
    accent: str = "#4F46E5"          # Indigo
    accent_hover: str = "#4338CA"
    accent_light: str = "#EEF2FF"
    
    # Status
    success: str = "#10B981"
    warning: str = "#F59E0B"
    error: str = "#EF4444"
    info: str = "#3B82F6"
    
    # Borders
    border: str = "#E5E7EB"
    border_focus: str = "#4F46E5"


THEME = Theme()


# ═══════════════════════════════════════════════════════════════════════════════
# OLLAMA NLP ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class OllamaNLP:
    """
    Natural Language Processing using Ollama models.
    - llama3.2:3b for understanding and planning
    - llava:7b for vision analysis
    """
    
    def __init__(self):
        self.base_url = "http://localhost:11434"
        self.planner_model = "llama3.2:3b"
        self.vision_model = "llava:7b"
        self.timeout = 60
        
        # System prompt for the agent
        self.system_prompt = """You are a friendly and intelligent macOS AI assistant. Your name is "macOS AI Agent".
You can have natural conversations AND help users control their computer.

## About You
- You are a helpful AI assistant that runs on macOS
- You can control system settings, open apps, browse the web, and have conversations
- You're powered by Llama 3.2 for understanding and LLaVA for vision analysis

## Available Actions (only use when user wants to DO something)
1. SYSTEM: wifi_on, wifi_off, bluetooth_on, bluetooth_off, volume_up, volume_down, volume_set, mute, unmute, dark_mode_on, dark_mode_off, screenshot, lock, sleep
2. APPS: open_app (with app name), close_app
3. BROWSER: open_url (with url)
4. YOUTUBE: youtube_play (with query) - searches YouTube and plays the first result
5. SCREEN INTERACTION: find_and_click (with element description), click (with x,y), type_text (with text), press_key (with key like 'enter', 'tab'), hotkey (with keys array like ['command', 'c'])
6. FLOW: wait (with seconds)

IMPORTANT: For playing videos/songs on YouTube, ALWAYS use "youtube_play" action with the search query.

## Response Format (JSON)
{
    "understood": true,
    "is_conversation": true/false,
    "intent": "what user wants",
    "actions": [],
    "response": "your friendly response",
    "needs_clarification": false
}

## Examples

User: "hi" or "hello"
{"understood": true, "is_conversation": true, "intent": "greeting", "actions": [], "response": "Hello! I'm your macOS AI Assistant. I can help you control your computer - just ask me to turn on WiFi, open apps, adjust volume, or anything else! What would you like to do?", "needs_clarification": false}

User: "who are you"
{"understood": true, "is_conversation": true, "intent": "identity question", "actions": [], "response": "I'm your macOS AI Agent! I'm an intelligent assistant that can help you control your Mac using natural language. I can manage WiFi, Bluetooth, volume, open apps, browse websites, take screenshots, and more. Just tell me what you need!", "needs_clarification": false}

User: "what can you do"
{"understood": true, "is_conversation": true, "intent": "capabilities question", "actions": [], "response": "I can help you with many things! Here's what I can do:\\n• Control WiFi and Bluetooth\\n• Adjust volume and brightness\\n• Toggle dark/light mode\\n• Open apps and websites\\n• Take screenshots\\n• Lock your Mac\\nJust ask naturally, like 'turn on wifi' or 'open Safari'!", "needs_clarification": false}

User: "turn on wifi"
{"understood": true, "is_conversation": false, "intent": "enable wifi", "actions": [{"type": "wifi_on", "params": {}}], "response": "Turning on WiFi for you!", "needs_clarification": false}

User: "open youtube"
{"understood": true, "is_conversation": false, "intent": "open youtube", "actions": [{"type": "open_url", "params": {"url": "https://youtube.com"}}], "response": "Opening YouTube now!", "needs_clarification": false}

User: "set volume to 50"
{"understood": true, "is_conversation": false, "intent": "set volume", "actions": [{"type": "volume_set", "params": {"level": 50}}], "response": "Setting volume to 50%", "needs_clarification": false}

User: "play hoyna hoyna song on youtube" or "open youtube and play [song name]"
{"understood": true, "is_conversation": false, "intent": "play song on youtube", "actions": [{"type": "youtube_play", "params": {"query": "hoyna hoyna song"}}], "response": "Playing Hoyna Hoyna on YouTube for you!", "needs_clarification": false}

User: "play despacito" or "play [any song/video]"
{"understood": true, "is_conversation": false, "intent": "play on youtube", "actions": [{"type": "youtube_play", "params": {"query": "despacito"}}], "response": "Playing Despacito on YouTube!", "needs_clarification": false}

User: "click on the search bar"
{"understood": true, "is_conversation": false, "intent": "click search", "actions": [{"type": "find_and_click", "params": {"element": "search bar or search input field"}}], "response": "Clicking on the search bar!", "needs_clarification": false}

User: "type hello world"
{"understood": true, "is_conversation": false, "intent": "type text", "actions": [{"type": "type_text", "params": {"text": "hello world"}}], "response": "Typing 'hello world'", "needs_clarification": false}

User: "press enter"
{"understood": true, "is_conversation": false, "intent": "press key", "actions": [{"type": "press_key", "params": {"key": "enter"}}], "response": "Pressing Enter", "needs_clarification": false}

User: "thanks" or "thank you"
{"understood": true, "is_conversation": true, "intent": "gratitude", "actions": [], "response": "You're welcome! Let me know if you need anything else. 😊", "needs_clarification": false}

Be conversational and friendly! Always respond with valid JSON."""
    
    def is_available(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def get_models(self) -> list:
        """Get list of available models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except:
            pass
        return []
    
    def understand(self, user_input: str, context: str = "") -> Dict[str, Any]:
        """
        Process natural language input and return structured response.
        Uses llama3.2:3b for understanding.
        """
        prompt = f"""User request: {user_input}

{f'Context: {context}' if context else ''}

Analyze this request and respond with a JSON object containing your understanding and the actions to take."""

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.planner_model,
                    "prompt": prompt,
                    "system": self.system_prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 500
                    }
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get("response", "")
                
                # Parse JSON response
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    # Try to extract JSON from response
                    import re
                    json_match = re.search(r'\{.*\}', text, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
                    
                    return {
                        "understood": False,
                        "response": "I had trouble understanding that. Could you rephrase?",
                        "actions": []
                    }
        except Exception as e:
            return {
                "understood": False,
                "response": f"Error communicating with AI: {str(e)}",
                "actions": []
            }
    
    def chat(self, message: str, history: list = None) -> str:
        """Simple chat response without action parsing."""
        messages = history or []
        messages.append({"role": "user", "content": message})
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.planner_model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.7}
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("message", {}).get("content", "")
        except:
            pass
        
        return "I'm having trouble responding right now."
    
    def analyze_image(self, image_path: str, question: str = "What's on this screen?") -> str:
        """Analyze an image using llava:7b vision model."""
        import base64
        
        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.vision_model,
                    "prompt": question,
                    "images": [image_data],
                    "stream": False,
                    "options": {"temperature": 0.3}
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "Unable to analyze image")
        except Exception as e:
            return f"Vision analysis error: {str(e)}"
        
        return "Vision analysis unavailable"
    
    def find_element(self, image_path: str, element_description: str) -> Dict[str, Any]:
        """Find an element on screen and return its coordinates."""
        import base64
        
        # Get screen dimensions
        try:
            import subprocess
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True
            )
            # Default to common MacBook resolution
            screen_width, screen_height = 1440, 900
        except:
            screen_width, screen_height = 1440, 900
        
        prompt = f"""You are analyzing a macOS screenshot to find a UI element.

TASK: Find "{element_description}" in this image.

The screen resolution is approximately {screen_width}x{screen_height} pixels.
Coordinates start from (0,0) at TOP-LEFT corner.

Look carefully at the image and identify the element. Common locations:
- YouTube video thumbnails are usually in the center-left area, around x=300-600, y=200-500
- Search bars are usually at the top, around y=50-150
- Play buttons are in the center of video players
- Navigation is usually on the left side

You MUST respond with ONLY this JSON format:
{{"found": true, "x": 400, "y": 300, "description": "found the video thumbnail"}}

OR if not found:
{{"found": false, "x": 0, "y": 0, "description": "element not visible"}}

Respond with ONLY the JSON, no other text."""

        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.vision_model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 100}
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get("response", "").strip()
                
                # Try to parse JSON
                try:
                    parsed = json.loads(text)
                    if parsed.get("found") and parsed.get("x") and parsed.get("y"):
                        return parsed
                except:
                    pass
                
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{[^}]+\}', text)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                        if parsed.get("x") and parsed.get("y"):
                            parsed["found"] = True
                            return parsed
                    except:
                        pass
                
                # Try to extract numbers if JSON fails
                numbers = re.findall(r'\d+', text)
                if len(numbers) >= 2:
                    x, y = int(numbers[0]), int(numbers[1])
                    if 0 < x < 2000 and 0 < y < 1500:
                        return {"found": True, "x": x, "y": y, "description": "extracted coordinates"}
                        
        except Exception as e:
            print(f"Vision error: {e}")
        
        return {"found": False, "description": "Could not analyze screen"}


# ═══════════════════════════════════════════════════════════════════════════════
# SCREEN INTERACTOR - Vision-guided clicking
# ═══════════════════════════════════════════════════════════════════════════════

class ScreenInteractor:
    """Interact with screen elements using vision + clicking"""
    
    def __init__(self, nlp: OllamaNLP):
        self.nlp = nlp
        self.screenshot_path = "/tmp/agent_screenshot.png"
    
    def take_screenshot(self) -> str:
        """Take a screenshot and return path"""
        import subprocess
        subprocess.run(
            ["screencapture", "-x", self.screenshot_path],
            check=True
        )
        return self.screenshot_path
    
    def click_at(self, x: int, y: int) -> bool:
        """Click at coordinates using AppleScript for reliability"""
        try:
            import subprocess
            # Use cliclick if available, otherwise AppleScript
            try:
                subprocess.run(["cliclick", f"c:{x},{y}"], check=True)
                return True
            except FileNotFoundError:
                pass
            
            # Fallback to pyautogui
            import pyautogui
            pyautogui.click(x, y)
            return True
        except Exception as e:
            print(f"Click error: {e}")
            return False
    
    def find_and_click(self, element_description: str, callback=None) -> Dict[str, Any]:
        """Find an element on screen and click it"""
        if callback:
            callback("📸 Taking screenshot...")
        
        # Take screenshot
        self.take_screenshot()
        
        if callback:
            callback("🔍 Analyzing screen with LLaVA...")
        
        # Find element using vision
        result = self.nlp.find_element(self.screenshot_path, element_description)
        
        if result.get("found") and result.get("x") and result.get("y"):
            x, y = int(result["x"]), int(result["y"])
            
            if callback:
                callback(f"🎯 Found at ({x}, {y}), clicking...")
            
            import time
            time.sleep(0.5)  # Small delay
            
            if self.click_at(x, y):
                return {
                    "success": True,
                    "message": f"Clicked on '{element_description}' at ({x}, {y})",
                    "coordinates": (x, y)
                }
            else:
                return {"success": False, "message": "Failed to click"}
        else:
            # Fallback: try keyboard navigation for common scenarios
            if callback:
                callback("🔄 Trying keyboard navigation fallback...")
            return self._keyboard_fallback(element_description, callback)
    
    def _keyboard_fallback(self, element_description: str, callback=None) -> Dict[str, Any]:
        """Fallback to keyboard navigation when vision fails"""
        import time
        
        try:
            import pyautogui
            
            desc_lower = element_description.lower()
            
            # YouTube video result - Tab to first result and Enter
            if any(word in desc_lower for word in ["video", "thumbnail", "result", "first"]):
                if callback:
                    callback("⌨️ Using Tab to navigate to video...")
                # Tab a few times to reach the first video, then Enter
                time.sleep(0.5)
                pyautogui.press('tab')
                time.sleep(0.3)
                pyautogui.press('tab')
                time.sleep(0.3)
                pyautogui.press('tab')
                time.sleep(0.3)
                pyautogui.press('enter')
                return {"success": True, "message": "Navigated with keyboard and pressed Enter"}
            
            # Search bar
            elif "search" in desc_lower:
                pyautogui.hotkey('command', 'l')  # Focus URL/search bar
                time.sleep(0.2)
                return {"success": True, "message": "Focused search/URL bar with Cmd+L"}
            
            # Play button
            elif "play" in desc_lower:
                pyautogui.press('space')  # Space plays/pauses videos
                return {"success": True, "message": "Pressed Space to play"}
            
            else:
                return {"success": False, "message": f"Could not find '{element_description}'"}
                
        except Exception as e:
            return {"success": False, "message": f"Keyboard fallback failed: {e}"}
    
    def type_text(self, text: str) -> bool:
        """Type text using keyboard"""
        try:
            import pyautogui
            pyautogui.write(text, interval=0.05)
            return True
        except:
            return False
    
    def press_key(self, key: str) -> bool:
        """Press a key"""
        try:
            import pyautogui
            pyautogui.press(key)
            return True
        except:
            return False
    
    def hotkey(self, *keys) -> bool:
        """Press hotkey combination"""
        try:
            import pyautogui
            pyautogui.hotkey(*keys)
            return True
        except:
            return False


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM EXECUTOR
# ═══════════════════════════════════════════════════════════════════════════════

class SystemExecutor:
    """Execute system commands on macOS"""
    
    def __init__(self, screen_interactor: ScreenInteractor = None):
        self.screen = screen_interactor
    
    COMMANDS = {
        "wifi_on": "networksetup -setairportpower en0 on",
        "wifi_off": "networksetup -setairportpower en0 off",
        "bluetooth_on": "blueutil -p 1",
        "bluetooth_off": "blueutil -p 0",
        "volume_up": "osascript -e 'set volume output volume ((output volume of (get volume settings)) + 10)'",
        "volume_down": "osascript -e 'set volume output volume ((output volume of (get volume settings)) - 10)'",
        "mute": "osascript -e 'set volume output muted true'",
        "unmute": "osascript -e 'set volume output muted false'",
        "brightness_up": "brightness 0.1",
        "brightness_down": "brightness -0.1",
        "dark_mode_on": "osascript -e 'tell app \"System Events\" to tell appearance preferences to set dark mode to true'",
        "dark_mode_off": "osascript -e 'tell app \"System Events\" to tell appearance preferences to set dark mode to false'",
        "sleep": "pmset displaysleepnow",
        "lock": "pmset displaysleepnow",
        "screenshot": "screencapture -x ~/Desktop/screenshot_$(date +%Y%m%d_%H%M%S).png",
    }
    
    def execute(self, action_type: str, params: dict = None, callback=None) -> Dict[str, Any]:
        """Execute an action"""
        import subprocess
        
        params = params or {}
        
        try:
            # Direct system commands
            if action_type in self.COMMANDS:
                cmd = self.COMMANDS[action_type]
                subprocess.run(cmd, shell=True, check=True, capture_output=True)
                return {"success": True, "message": f"Executed {action_type}"}
            
            # Volume set
            elif action_type == "volume_set":
                level = params.get("level", 50)
                cmd = f"osascript -e 'set volume output volume {level}'"
                subprocess.run(cmd, shell=True, check=True)
                return {"success": True, "message": f"Volume set to {level}%"}
            
            # Open app
            elif action_type == "open_app":
                app = params.get("app", "")
                cmd = f"open -a '{app}'"
                subprocess.run(cmd, shell=True, check=True)
                return {"success": True, "message": f"Opened {app}"}
            
            # Close app
            elif action_type == "close_app":
                app = params.get("app", "")
                cmd = f"osascript -e 'quit app \"{app}\"'"
                subprocess.run(cmd, shell=True, check=True)
                return {"success": True, "message": f"Closed {app}"}
            
            # Open URL
            elif action_type == "open_url":
                url = params.get("url", "")
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                cmd = f"open '{url}'"
                subprocess.run(cmd, shell=True, check=True)
                return {"success": True, "message": f"Opened {url}"}
            
            # YouTube search and play - reliable keyboard-based approach
            elif action_type == "youtube_play":
                query = params.get("query", "")
                import time
                import urllib.parse
                
                # Open YouTube search
                encoded_query = urllib.parse.quote(query)
                url = f"https://www.youtube.com/results?search_query={encoded_query}"
                subprocess.run(f"open '{url}'", shell=True, check=True)
                
                if callback:
                    callback("🎬 Opening YouTube search...")
                
                # Wait for page to load
                time.sleep(4)
                
                if callback:
                    callback("⌨️ Navigating to first video...")
                
                try:
                    import pyautogui
                    # Tab to skip filters and reach first video
                    for _ in range(3):
                        pyautogui.press('tab')
                        time.sleep(0.2)
                    
                    # Press Enter to play
                    pyautogui.press('enter')
                    
                    return {"success": True, "message": f"Playing '{query}' on YouTube"}
                except ImportError:
                    return {"success": False, "message": "PyAutoGUI not installed"}
            
            # Find and click element (vision-guided)
            elif action_type == "find_and_click":
                if self.screen:
                    element = params.get("element", "")
                    return self.screen.find_and_click(element, callback)
                return {"success": False, "message": "Screen interactor not available"}
            
            # Click at coordinates
            elif action_type == "click":
                x = params.get("x", 0)
                y = params.get("y", 0)
                try:
                    import pyautogui
                    pyautogui.click(x, y)
                    return {"success": True, "message": f"Clicked at ({x}, {y})"}
                except ImportError:
                    return {"success": False, "message": "PyAutoGUI not installed"}
            
            # Type text
            elif action_type == "type_text":
                text = params.get("text", "")
                try:
                    import pyautogui
                    pyautogui.write(text, interval=0.03)
                    return {"success": True, "message": f"Typed: {text[:20]}..."}
                except ImportError:
                    return {"success": False, "message": "PyAutoGUI not installed"}
            
            # Press key
            elif action_type == "press_key":
                key = params.get("key", "")
                try:
                    import pyautogui
                    pyautogui.press(key)
                    return {"success": True, "message": f"Pressed {key}"}
                except ImportError:
                    return {"success": False, "message": "PyAutoGUI not installed"}
            
            # Hotkey
            elif action_type == "hotkey":
                keys = params.get("keys", [])
                try:
                    import pyautogui
                    pyautogui.hotkey(*keys)
                    return {"success": True, "message": f"Pressed {'+'.join(keys)}"}
                except ImportError:
                    return {"success": False, "message": "PyAutoGUI not installed"}
            
            # Wait
            elif action_type == "wait":
                import time
                seconds = params.get("seconds", 1)
                time.sleep(seconds)
                return {"success": True, "message": f"Waited {seconds}s"}
            
            else:
                return {"success": False, "message": f"Unknown action: {action_type}"}
                
        except subprocess.CalledProcessError as e:
            return {"success": False, "message": f"Command failed: {e}"}
        except Exception as e:
            return {"success": False, "message": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# PROFESSIONAL GUI
# ═══════════════════════════════════════════════════════════════════════════════

class ProfessionalAgentGUI:
    """
    Professional, clean white-themed GUI for the macOS AI Agent.
    All interactions are processed through Ollama NLP.
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("macOS AI Agent")
        self.root.geometry("1000x700")
        self.root.minsize(900, 600)
        self.root.configure(bg=THEME.bg_primary)
        
        # State
        self.is_processing = False
        self.conversation_history = []
        
        # Components
        self.nlp = OllamaNLP()
        self.screen = ScreenInteractor(self.nlp)
        self.executor = SystemExecutor(self.screen)
        
        # Message queue
        self.msg_queue = queue.Queue()
        
        # Build UI
        self._setup_styles()
        self._create_layout()
        self._check_ollama()
        self._process_messages()
    
    def _setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Frame styles
        style.configure("Card.TFrame", background=THEME.bg_card)
        style.configure("Secondary.TFrame", background=THEME.bg_secondary)
    
    def _create_layout(self):
        """Create the main layout"""
        # Main container with padding
        main = tk.Frame(self.root, bg=THEME.bg_primary)
        main.pack(fill=tk.BOTH, expand=True, padx=30, pady=25)
        
        # Header
        self._create_header(main)
        
        # Content area (two columns)
        content = tk.Frame(main, bg=THEME.bg_primary)
        content.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        # Left column - Chat
        self._create_chat_panel(content)
        
        # Right column - Quick Actions & Status
        self._create_side_panel(content)
    
    def _create_header(self, parent):
        """Create header section"""
        header = tk.Frame(parent, bg=THEME.bg_primary)
        header.pack(fill=tk.X)
        
        # Logo and title
        title_frame = tk.Frame(header, bg=THEME.bg_primary)
        title_frame.pack(side=tk.LEFT)
        
        # AI Icon
        icon_label = tk.Label(
            title_frame,
            text="🤖",
            font=("SF Pro Display", 28),
            bg=THEME.bg_primary
        )
        icon_label.pack(side=tk.LEFT, padx=(0, 12))
        
        # Title text
        title_text = tk.Frame(title_frame, bg=THEME.bg_primary)
        title_text.pack(side=tk.LEFT)
        
        tk.Label(
            title_text,
            text="macOS AI Agent",
            font=("SF Pro Display", 22, "bold"),
            fg=THEME.text_primary,
            bg=THEME.bg_primary
        ).pack(anchor=tk.W)
        
        tk.Label(
            title_text,
            text="Powered by Llama 3.2 & LLaVA",
            font=("SF Pro Display", 11),
            fg=THEME.text_secondary,
            bg=THEME.bg_primary
        ).pack(anchor=tk.W)
        
        # Status indicator (right side)
        status_frame = tk.Frame(header, bg=THEME.bg_primary)
        status_frame.pack(side=tk.RIGHT)
        
        self.status_canvas = tk.Canvas(
            status_frame,
            width=10, height=10,
            bg=THEME.bg_primary,
            highlightthickness=0
        )
        self.status_canvas.pack(side=tk.LEFT, padx=(0, 8))
        self.status_canvas.create_oval(1, 1, 9, 9, fill=THEME.warning, outline="")
        
        self.status_text = tk.Label(
            status_frame,
            text="Checking...",
            font=("SF Pro Display", 11),
            fg=THEME.text_secondary,
            bg=THEME.bg_primary
        )
        self.status_text.pack(side=tk.LEFT)
    
    def _create_chat_panel(self, parent):
        """Create the main chat panel"""
        # Chat container (left side, expandable)
        chat_frame = tk.Frame(parent, bg=THEME.bg_primary)
        chat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20))
        
        # Chat card
        chat_card = tk.Frame(
            chat_frame,
            bg=THEME.bg_card,
            highlightbackground=THEME.border,
            highlightthickness=1
        )
        chat_card.pack(fill=tk.BOTH, expand=True)
        
        # Chat header
        chat_header = tk.Frame(chat_card, bg=THEME.bg_card)
        chat_header.pack(fill=tk.X, padx=20, pady=(15, 10))
        
        tk.Label(
            chat_header,
            text="💬 Chat",
            font=("SF Pro Display", 14, "bold"),
            fg=THEME.text_primary,
            bg=THEME.bg_card
        ).pack(side=tk.LEFT)
        
        # Clear button
        clear_btn = tk.Button(
            chat_header,
            text="Clear",
            font=("SF Pro Display", 10),
            fg=THEME.text_secondary,
            bg=THEME.bg_card,
            activebackground=THEME.bg_secondary,
            relief="flat",
            cursor="hand2",
            command=self._clear_chat
        )
        clear_btn.pack(side=tk.RIGHT)
        
        # Divider
        tk.Frame(chat_card, height=1, bg=THEME.border).pack(fill=tk.X, padx=20)
        
        # Chat messages area
        self.chat_area = scrolledtext.ScrolledText(
            chat_card,
            font=("SF Pro Text", 12),
            bg=THEME.bg_card,
            fg=THEME.text_primary,
            relief="flat",
            wrap=tk.WORD,
            state=tk.DISABLED,
            padx=10,
            pady=10
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Configure chat tags
        self.chat_area.tag_configure("user", foreground=THEME.accent, font=("SF Pro Text", 12, "bold"))
        self.chat_area.tag_configure("user_msg", foreground=THEME.text_primary)
        self.chat_area.tag_configure("agent", foreground=THEME.success, font=("SF Pro Text", 12, "bold"))
        self.chat_area.tag_configure("agent_msg", foreground=THEME.text_secondary)
        self.chat_area.tag_configure("success", foreground=THEME.success)
        self.chat_area.tag_configure("error", foreground=THEME.error)
        self.chat_area.tag_configure("system", foreground=THEME.text_muted, font=("SF Pro Text", 10, "italic"))
        
        # Input area
        input_frame = tk.Frame(chat_card, bg=THEME.bg_secondary)
        input_frame.pack(fill=tk.X, padx=15, pady=15)
        
        # Input field
        self.input_entry = tk.Entry(
            input_frame,
            font=("SF Pro Text", 13),
            bg=THEME.bg_primary,
            fg=THEME.text_primary,
            insertbackground=THEME.text_primary,
            relief="flat",
            highlightthickness=2,
            highlightbackground=THEME.border,
            highlightcolor=THEME.accent
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=12, padx=(0, 10))
        self.input_entry.bind("<Return>", lambda e: self._send_message())
        
        # Placeholder
        self.input_entry.insert(0, "Ask me anything...")
        self.input_entry.config(fg=THEME.text_muted)
        self.input_entry.bind("<FocusIn>", self._on_input_focus)
        self.input_entry.bind("<FocusOut>", self._on_input_blur)
        
        # Send button
        self.send_btn = tk.Button(
            input_frame,
            text="Send →",
            font=("SF Pro Display", 11, "bold"),
            fg="white",
            bg=THEME.accent,
            activebackground=THEME.accent_hover,
            activeforeground="white",
            relief="flat",
            padx=25,
            pady=10,
            cursor="hand2",
            command=self._send_message
        )
        self.send_btn.pack(side=tk.RIGHT)
    
    def _create_side_panel(self, parent):
        """Create the side panel with quick actions"""
        side_frame = tk.Frame(parent, bg=THEME.bg_primary, width=280)
        side_frame.pack(side=tk.RIGHT, fill=tk.Y)
        side_frame.pack_propagate(False)
        
        # Quick Actions Card
        actions_card = tk.Frame(
            side_frame,
            bg=THEME.bg_card,
            highlightbackground=THEME.border,
            highlightthickness=1
        )
        actions_card.pack(fill=tk.X, pady=(0, 15))
        
        # Header
        tk.Label(
            actions_card,
            text="⚡ Quick Actions",
            font=("SF Pro Display", 13, "bold"),
            fg=THEME.text_primary,
            bg=THEME.bg_card
        ).pack(anchor=tk.W, padx=15, pady=(15, 10))
        
        tk.Frame(actions_card, height=1, bg=THEME.border).pack(fill=tk.X, padx=15)
        
        # Action buttons grid
        btn_container = tk.Frame(actions_card, bg=THEME.bg_card)
        btn_container.pack(fill=tk.X, padx=15, pady=15)
        
        actions = [
            ("📶", "WiFi On", "wifi_on"),
            ("📴", "WiFi Off", "wifi_off"),
            ("🔊", "Vol Up", "volume_up"),
            ("🔉", "Vol Down", "volume_down"),
            ("🔇", "Mute", "mute"),
            ("🔈", "Unmute", "unmute"),
            ("🌙", "Dark", "dark_mode_on"),
            ("☀️", "Light", "dark_mode_off"),
            ("📷", "Screenshot", "screenshot"),
            ("🔒", "Lock", "lock"),
        ]
        
        for i, (icon, label, cmd) in enumerate(actions):
            row, col = divmod(i, 2)
            
            btn = tk.Button(
                btn_container,
                text=f"{icon} {label}",
                font=("SF Pro Text", 10),
                fg=THEME.text_primary,
                bg=THEME.bg_secondary,
                activebackground=THEME.accent_light,
                activeforeground=THEME.accent,
                relief="flat",
                padx=8,
                pady=8,
                cursor="hand2",
                command=lambda c=cmd: self._quick_action(c)
            )
            btn.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
        
        btn_container.columnconfigure(0, weight=1)
        btn_container.columnconfigure(1, weight=1)
        
        # Model Status Card
        status_card = tk.Frame(
            side_frame,
            bg=THEME.bg_card,
            highlightbackground=THEME.border,
            highlightthickness=1
        )
        status_card.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(
            status_card,
            text="🧠 AI Models",
            font=("SF Pro Display", 13, "bold"),
            fg=THEME.text_primary,
            bg=THEME.bg_card
        ).pack(anchor=tk.W, padx=15, pady=(15, 10))
        
        tk.Frame(status_card, height=1, bg=THEME.border).pack(fill=tk.X, padx=15)
        
        # Model status items
        models_frame = tk.Frame(status_card, bg=THEME.bg_card)
        models_frame.pack(fill=tk.X, padx=15, pady=15)
        
        # Llama model
        self.llama_status = self._create_model_status(
            models_frame, "Llama 3.2 (3B)", "Checking..."
        )
        
        # LLaVA model
        self.llava_status = self._create_model_status(
            models_frame, "LLaVA (7B)", "Checking..."
        )
        
        # Help Card
        help_card = tk.Frame(
            side_frame,
            bg=THEME.accent_light,
            highlightbackground=THEME.border,
            highlightthickness=1
        )
        help_card.pack(fill=tk.X)
        
        tk.Label(
            help_card,
            text="💡 Try saying...",
            font=("SF Pro Display", 12, "bold"),
            fg=THEME.accent,
            bg=THEME.accent_light
        ).pack(anchor=tk.W, padx=15, pady=(12, 8))
        
        tips = [
            '"Turn on WiFi"',
            '"Open Safari"',
            '"Go to youtube.com"',
            '"Set volume to 50%"',
            '"Take a screenshot"',
            '"Enable dark mode"'
        ]
        
        for tip in tips:
            tk.Label(
                help_card,
                text=f"  • {tip}",
                font=("SF Pro Text", 10),
                fg=THEME.text_secondary,
                bg=THEME.accent_light,
                anchor=tk.W
            ).pack(anchor=tk.W, padx=15)
        
        tk.Frame(help_card, height=12, bg=THEME.accent_light).pack()
    
    def _create_model_status(self, parent, name: str, status: str) -> tk.Label:
        """Create a model status row"""
        row = tk.Frame(parent, bg=THEME.bg_card)
        row.pack(fill=tk.X, pady=4)
        
        tk.Label(
            row,
            text=name,
            font=("SF Pro Text", 11),
            fg=THEME.text_primary,
            bg=THEME.bg_card
        ).pack(side=tk.LEFT)
        
        status_label = tk.Label(
            row,
            text=status,
            font=("SF Pro Text", 10),
            fg=THEME.text_muted,
            bg=THEME.bg_card
        )
        status_label.pack(side=tk.RIGHT)
        
        return status_label
    
    def _on_input_focus(self, event):
        """Handle input focus"""
        if self.input_entry.get() == "Ask me anything...":
            self.input_entry.delete(0, tk.END)
            self.input_entry.config(fg=THEME.text_primary)
    
    def _on_input_blur(self, event):
        """Handle input blur"""
        if not self.input_entry.get():
            self.input_entry.insert(0, "Ask me anything...")
            self.input_entry.config(fg=THEME.text_muted)
    
    def _check_ollama(self):
        """Check Ollama status and models"""
        def check():
            if self.nlp.is_available():
                models = self.nlp.get_models()
                
                # Update status
                self.msg_queue.put(("status", ("Ready", THEME.success)))
                
                # Check models
                has_llama = any("llama" in m.lower() for m in models)
                has_llava = any("llava" in m.lower() for m in models)
                
                self.msg_queue.put(("llama_status", "Ready ✓" if has_llama else "Not found"))
                self.msg_queue.put(("llava_status", "Ready ✓" if has_llava else "Not found"))
                
                self.msg_queue.put(("chat", ("system", "🤖 AI Agent ready. How can I help you today?")))
                
                if not has_llama:
                    self.msg_queue.put(("chat", ("system", "⚠️ Run 'ollama pull llama3.2:3b' for best experience")))
            else:
                self.msg_queue.put(("status", ("Offline", THEME.error)))
                self.msg_queue.put(("llama_status", "Offline"))
                self.msg_queue.put(("llava_status", "Offline"))
                self.msg_queue.put(("chat", ("error", "❌ Ollama not running. Start with: ollama serve")))
        
        threading.Thread(target=check, daemon=True).start()
    
    def _send_message(self):
        """Send user message and process with NLP"""
        message = self.input_entry.get().strip()
        
        if not message or message == "Ask me anything...":
            return
        
        if self.is_processing:
            return
        
        # Clear input
        self.input_entry.delete(0, tk.END)
        
        # Show user message
        self._add_chat("You", message, "user")
        
        # Process with NLP
        self.is_processing = True
        self._update_status("Thinking...", THEME.warning)
        
        threading.Thread(
            target=self._process_with_nlp,
            args=(message,),
            daemon=True
        ).start()
    
    def _process_with_nlp(self, message: str):
        """Process message using Ollama NLP"""
        try:
            # Get NLP understanding
            result = self.nlp.understand(message)
            
            if result.get("understood"):
                response = result.get("response", "")
                actions = result.get("actions", [])
                
                # Show agent response
                self.msg_queue.put(("chat", ("agent", response)))
                
                # Callback for status updates during vision operations
                def status_callback(msg):
                    self.msg_queue.put(("chat", ("system", f"  {msg}")))
                
                # Execute actions
                if actions:
                    for action in actions:
                        action_type = action.get("type", "")
                        params = action.get("params", {})
                        
                        # Show what we're doing
                        if action_type == "find_and_click":
                            element = params.get("element", "")
                            self.msg_queue.put(("chat", ("system", f"  🔍 Looking for: {element}")))
                        
                        exec_result = self.executor.execute(action_type, params, callback=status_callback)
                        
                        if exec_result.get("success"):
                            self.msg_queue.put(("chat", ("success", f"  ✓ {exec_result.get('message')}")))
                        else:
                            self.msg_queue.put(("chat", ("error", f"  ✗ {exec_result.get('message')}")))
                        
                        # Small delay between actions
                        import time
                        time.sleep(0.3)
                
                # Handle clarification
                if result.get("needs_clarification"):
                    question = result.get("clarification_question", "")
                    if question:
                        self.msg_queue.put(("chat", ("agent", f"❓ {question}")))
            else:
                self.msg_queue.put(("chat", ("agent", result.get("response", "I'm not sure how to help with that."))))
            
            self.msg_queue.put(("status", ("Ready", THEME.success)))
            
        except Exception as e:
            self.msg_queue.put(("chat", ("error", f"Error: {str(e)}")))
            self.msg_queue.put(("status", ("Error", THEME.error)))
        
        finally:
            self.is_processing = False
    
    def _quick_action(self, action: str):
        """Execute quick action"""
        self._add_chat("", f"⚡ Executing: {action.replace('_', ' ').title()}", "system")
        
        result = self.executor.execute(action)
        
        if result.get("success"):
            self._add_chat("", f"✓ {result.get('message')}", "success")
        else:
            self._add_chat("", f"✗ {result.get('message')}", "error")
    
    def _add_chat(self, sender: str, message: str, tag: str):
        """Add message to chat"""
        self.chat_area.config(state=tk.NORMAL)
        
        timestamp = time.strftime("%H:%M")
        
        if tag == "user":
            self.chat_area.insert(tk.END, f"\n[{timestamp}] You: ", "user")
            self.chat_area.insert(tk.END, f"{message}\n", "user_msg")
        elif tag == "agent":
            self.chat_area.insert(tk.END, f"\n[{timestamp}] Agent: ", "agent")
            self.chat_area.insert(tk.END, f"{message}\n", "agent_msg")
        elif tag == "success":
            self.chat_area.insert(tk.END, f"{message}\n", "success")
        elif tag == "error":
            self.chat_area.insert(tk.END, f"{message}\n", "error")
        elif tag == "system":
            self.chat_area.insert(tk.END, f"\n{message}\n", "system")
        
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)
    
    def _clear_chat(self):
        """Clear chat history"""
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.delete(1.0, tk.END)
        self.chat_area.config(state=tk.DISABLED)
        self.conversation_history = []
        self._add_chat("", "🤖 Chat cleared. How can I help you?", "system")
    
    def _update_status(self, text: str, color: str):
        """Update status indicator"""
        self.status_text.config(text=text)
        self.status_canvas.delete("all")
        self.status_canvas.create_oval(1, 1, 9, 9, fill=color, outline="")
    
    def _process_messages(self):
        """Process messages from background threads"""
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()
                
                if msg_type == "chat":
                    tag, message = data
                    self._add_chat("", message, tag)
                elif msg_type == "status":
                    text, color = data
                    self._update_status(text, color)
                elif msg_type == "llama_status":
                    self.llama_status.config(
                        text=data,
                        fg=THEME.success if "✓" in data else THEME.error
                    )
                elif msg_type == "llava_status":
                    self.llava_status.config(
                        text=data,
                        fg=THEME.success if "✓" in data else THEME.error
                    )
        except queue.Empty:
            pass
        
        self.root.after(100, self._process_messages)
    
    def run(self):
        """Run the application"""
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 1000) // 2
        y = (self.root.winfo_screenheight() - 700) // 2
        self.root.geometry(f"1000x700+{x}+{y}")
        
        self.root.mainloop()


def main():
    """Main entry point"""
    app = ProfessionalAgentGUI()
    app.run()


if __name__ == "__main__":
    main()
