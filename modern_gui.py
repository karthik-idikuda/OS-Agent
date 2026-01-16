"""
Professional Modern GUI for macOS AI Agent v2.0

Features:
- Dark theme with glassmorphism effects
- Gradient accents and dynamic animations
- Real-time task progress visualization
- Screenshot preview panel
- Quick action buttons
- Integration with message bus for live updates
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import time
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass

# Import agent components
try:
    from agent.core import Orchestrator, message_bus, EventType, OrchestratorState
    from agent.commands import command_registry
    from agent.voice import EnhancedVoiceInterface, TTSVoice
    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False
    print("Warning: Agent modules not available. Running in demo mode.")


# ═══════════════════════════════════════════════════════════════════════════════
# MODERN DARK THEME
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ModernTheme:
    """Professional dark theme with vibrant accents"""
    # Backgrounds
    bg_primary: str = "#0F0F14"        # Deep black
    bg_secondary: str = "#16161D"      # Slightly lighter
    bg_tertiary: str = "#1E1E28"       # Card background
    bg_glass: str = "#1E1E2899"        # Glassmorphism
    bg_input: str = "#252532"          # Input fields
    
    # Text
    text_primary: str = "#FFFFFF"
    text_secondary: str = "#A0A0B0"
    text_muted: str = "#6B6B7B"
    
    # Gradients / Accents
    accent_start: str = "#6366F1"      # Indigo
    accent_end: str = "#8B5CF6"        # Purple
    accent_hover: str = "#7C3AED"
    accent_glow: str = "#6366F133"
    
    # Status colors
    success: str = "#10B981"
    success_glow: str = "#10B98133"
    warning: str = "#F59E0B"
    error: str = "#EF4444"
    info: str = "#3B82F6"
    
    # Borders
    border: str = "#2E2E3A"
    border_focus: str = "#6366F1"


THEME = ModernTheme()


# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM WIDGETS
# ═══════════════════════════════════════════════════════════════════════════════

class GradientButton(tk.Canvas):
    """Button with gradient background and hover effects"""
    
    def __init__(self, parent, text, command=None, width=120, height=40, **kwargs):
        super().__init__(parent, width=width, height=height, 
                        highlightthickness=0, bg=THEME.bg_primary, **kwargs)
        
        self.text = text
        self.command = command
        self.width = width
        self.height = height
        self._hovered = False
        
        self.draw()
        
        # Bindings
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
    
    def draw(self):
        self.delete("all")
        
        # Draw rounded rectangle with gradient effect
        color = THEME.accent_hover if self._hovered else THEME.accent_start
        
        # Main button shape
        radius = 8
        self.create_rounded_rect(2, 2, self.width-2, self.height-2, radius, 
                                fill=color, outline="")
        
        # Top highlight for 3D effect
        self.create_rounded_rect(3, 3, self.width-3, self.height//2, radius,
                                fill=THEME.accent_end, outline="")
        
        # Text
        self.create_text(self.width//2, self.height//2, text=self.text,
                        fill=THEME.text_primary, font=("SF Pro Display", 12, "bold"))
    
    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def _on_enter(self, e):
        self._hovered = True
        self.draw()
    
    def _on_leave(self, e):
        self._hovered = False
        self.draw()
    
    def _on_click(self, e):
        if self.command:
            self.command()


class StatusIndicator(tk.Canvas):
    """Animated status indicator with glow effect"""
    
    def __init__(self, parent, size=12, **kwargs):
        super().__init__(parent, width=size*2, height=size*2,
                        highlightthickness=0, bg=THEME.bg_primary, **kwargs)
        self.size = size
        self.status = "idle"
        self._pulse_alpha = 0
        self._animating = False
        self.draw()
    
    def set_status(self, status: str):
        """Set status: idle, listening, thinking, executing, success, error"""
        self.status = status
        if status in ["listening", "thinking", "executing"]:
            self._start_pulse()
        else:
            self._animating = False
        self.draw()
    
    def draw(self):
        self.delete("all")
        
        colors = {
            "idle": THEME.text_muted,
            "listening": THEME.info,
            "thinking": THEME.warning,
            "executing": THEME.accent_start,
            "success": THEME.success,
            "error": THEME.error,
        }
        # Glow colors (lighter versions for outer ring)
        glow_colors = {
            "idle": "#3D3D4D",
            "listening": "#1E4A7A",
            "thinking": "#7A4F05",
            "executing": "#3A3A7A",
            "success": "#0A5A40",
            "error": "#7A2222",
        }
        color = colors.get(self.status, THEME.text_muted)
        glow = glow_colors.get(self.status, "#3D3D4D")
        
        # Glow effect (outer ring)
        self.create_oval(2, 2, self.size*2-2, self.size*2-2,
                        fill=glow, outline="")
        
        # Main circle
        self.create_oval(4, 4, self.size*2-4, self.size*2-4,
                        fill=color, outline="")
    
    def _start_pulse(self):
        if not self._animating:
            self._animating = True
            self._pulse()
    
    def _pulse(self):
        if not self._animating:
            return
        self._pulse_alpha = (self._pulse_alpha + 0.1) % 1.0
        self.draw()
        self.after(100, self._pulse)


class ProgressRing(tk.Canvas):
    """Circular progress indicator"""
    
    def __init__(self, parent, size=60, thickness=4, **kwargs):
        super().__init__(parent, width=size, height=size,
                        highlightthickness=0, bg=THEME.bg_tertiary, **kwargs)
        self.size = size
        self.thickness = thickness
        self.progress = 0
        self.draw()
    
    def set_progress(self, value: float):
        """Set progress 0-100"""
        self.progress = max(0, min(100, value))
        self.draw()
    
    def draw(self):
        self.delete("all")
        
        pad = self.thickness + 2
        
        # Background circle
        self.create_oval(pad, pad, self.size-pad, self.size-pad,
                        outline=THEME.border, width=self.thickness)
        
        # Progress arc
        extent = (self.progress / 100) * 360
        if extent > 0:
            self.create_arc(pad, pad, self.size-pad, self.size-pad,
                           start=90, extent=-extent,
                           style=tk.ARC, outline=THEME.accent_start,
                           width=self.thickness)
        
        # Center text
        self.create_text(self.size//2, self.size//2,
                        text=f"{int(self.progress)}%",
                        fill=THEME.text_primary,
                        font=("SF Pro Display", 11, "bold"))


class MessageBubble(tk.Frame):
    """Chat message bubble with modern styling"""
    
    def __init__(self, parent, text: str, is_user: bool = False, **kwargs):
        super().__init__(parent, bg=THEME.bg_secondary, **kwargs)
        
        # Container with proper alignment
        self.configure(padx=10, pady=5)
        
        # Bubble color based on sender
        bg = THEME.accent_start if is_user else THEME.bg_tertiary
        fg = THEME.text_primary
        
        # Bubble frame
        bubble = tk.Frame(self, bg=bg)
        bubble.pack(side=tk.RIGHT if is_user else tk.LEFT)
        
        # Message text
        label = tk.Label(bubble, text=text, bg=bg, fg=fg,
                        font=("SF Pro Display", 12),
                        wraplength=400, justify=tk.LEFT,
                        padx=15, pady=10)
        label.pack()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

class ModernAgentGUI:
    """
    Professional modern GUI for macOS AI Agent.
    
    Features:
    - Dark glassmorphism theme
    - Real-time status updates via message bus
    - Task progress visualization
    - Quick action buttons
    - Voice status indicator
    """
    
    def __init__(self):
        # Create main window
        self.root = tk.Tk()
        self.root.title("macOS AI Agent v2.0")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        self.root.configure(bg=THEME.bg_primary)
        
        # State
        self.is_processing = False
        self.current_step = 0
        self.total_steps = 0
        
        # Message queue for thread-safe UI updates (MUST be before _init_agent)
        self.msg_queue = queue.Queue()
        
        # Components
        self.orchestrator = None
        self.voice = None
        self._init_agent()
        
        # Build UI
        self._create_layout()
        self._setup_event_handlers()
        
        # Start message processor
        self._process_messages()
    
    def _init_agent(self):
        """Initialize agent components"""
        if AGENT_AVAILABLE:
            try:
                self.orchestrator = Orchestrator(
                    speak_callback=self._on_speak,
                    status_callback=self._on_status
                )
                self.voice = EnhancedVoiceInterface()
                self._queue_message("system", "Agent initialized successfully")
            except Exception as e:
                self._queue_message("error", f"Agent init error: {e}")
        else:
            self._queue_message("warning", "Running in demo mode - agent not available")
    
    def _setup_event_handlers(self):
        """Subscribe to message bus events"""
        if not AGENT_AVAILABLE:
            return
        
        message_bus.subscribe(EventType.TASK_STARTED, self._on_task_started)
        message_bus.subscribe(EventType.TASK_COMPLETED, self._on_task_completed)
        message_bus.subscribe(EventType.TASK_FAILED, self._on_task_failed)
        message_bus.subscribe(EventType.STEP_STARTED, self._on_step_started)
        message_bus.subscribe(EventType.STEP_COMPLETED, self._on_step_completed)
    
    # =========================================================================
    # Layout
    # =========================================================================
    
    def _create_layout(self):
        """Create the main layout"""
        # Main container
        main = tk.Frame(self.root, bg=THEME.bg_primary)
        main.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        
        # Header
        self._create_header(main)
        
        # Content (three columns)
        content = tk.Frame(main, bg=THEME.bg_primary)
        content.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        # Left: Quick Actions
        self._create_quick_actions(content)
        
        # Center: Chat
        self._create_chat_panel(content)
        
        # Right: Status & Progress
        self._create_status_panel(content)
    
    def _create_header(self, parent):
        """Create header with title and status"""
        header = tk.Frame(parent, bg=THEME.bg_primary)
        header.pack(fill=tk.X)
        
        # Left: Logo & Title
        left = tk.Frame(header, bg=THEME.bg_primary)
        left.pack(side=tk.LEFT)
        
        # Icon
        tk.Label(left, text="🤖", font=("SF Pro Display", 32),
                bg=THEME.bg_primary, fg=THEME.text_primary).pack(side=tk.LEFT, padx=(0, 15))
        
        # Title group
        title_group = tk.Frame(left, bg=THEME.bg_primary)
        title_group.pack(side=tk.LEFT)
        
        tk.Label(title_group, text="macOS AI Agent",
                font=("SF Pro Display", 24, "bold"),
                bg=THEME.bg_primary, fg=THEME.text_primary).pack(anchor=tk.W)
        
        tk.Label(title_group, text="Voice-Controlled Automation • v2.0",
                font=("SF Pro Display", 11),
                bg=THEME.bg_primary, fg=THEME.text_muted).pack(anchor=tk.W)
        
        # Right: Status indicator
        right = tk.Frame(header, bg=THEME.bg_primary)
        right.pack(side=tk.RIGHT)
        
        self.status_indicator = StatusIndicator(right)
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 10))
        
        self.status_label = tk.Label(right, text="Ready",
                                    font=("SF Pro Display", 12),
                                    bg=THEME.bg_primary, fg=THEME.text_secondary)
        self.status_label.pack(side=tk.LEFT)
    
    def _create_quick_actions(self, parent):
        """Create quick action buttons panel"""
        panel = tk.Frame(parent, bg=THEME.bg_tertiary, width=200)
        panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        panel.pack_propagate(False)
        
        # Title
        tk.Label(panel, text="Quick Actions",
                font=("SF Pro Display", 14, "bold"),
                bg=THEME.bg_tertiary, fg=THEME.text_primary).pack(pady=(20, 15), padx=15, anchor=tk.W)
        
        # Quick action buttons
        actions = [
            ("🎤 Start Listening", self._start_voice),
            ("📶 Toggle WiFi", lambda: self._quick_command("toggle wifi")),
            ("🔊 Volume Up", lambda: self._quick_command("volume up")),
            ("🔇 Mute", lambda: self._quick_command("mute")),
            ("🌙 Dark Mode", lambda: self._quick_command("dark mode on")),
            ("📸 Screenshot", lambda: self._quick_command("screenshot")),
            ("🌐 Open Safari", lambda: self._quick_command("open safari")),
            ("🎵 Open Spotify", lambda: self._quick_command("open spotify")),
        ]
        
        for text, cmd in actions:
            btn = tk.Button(panel, text=text, command=cmd,
                           font=("SF Pro Display", 11),
                           bg=THEME.bg_input, fg=THEME.text_primary,
                           activebackground=THEME.accent_start,
                           activeforeground=THEME.text_primary,
                           relief=tk.FLAT, cursor="hand2",
                           padx=15, pady=10)
            btn.pack(fill=tk.X, padx=15, pady=3)
            
            # Hover effect
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=THEME.border))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=THEME.bg_input))
        
        # Separator
        tk.Frame(panel, bg=THEME.border, height=1).pack(fill=tk.X, padx=15, pady=20)
        
        # Voice settings
        tk.Label(panel, text="Voice",
                font=("SF Pro Display", 12, "bold"),
                bg=THEME.bg_tertiary, fg=THEME.text_secondary).pack(padx=15, anchor=tk.W)
        
        # Voice selector
        self.voice_var = tk.StringVar(value="Aria (Female)")
        voices = ["Aria (Female)", "Jenny (Friendly)", "Guy (Male)", "Ryan (British)"]
        voice_menu = ttk.Combobox(panel, textvariable=self.voice_var, values=voices,
                                 state="readonly", width=20)
        voice_menu.pack(padx=15, pady=10)
    
    def _create_chat_panel(self, parent):
        """Create main chat panel"""
        panel = tk.Frame(parent, bg=THEME.bg_secondary)
        panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        
        # Chat messages area
        self.chat_frame = tk.Frame(panel, bg=THEME.bg_secondary)
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Scrollable chat container
        self.chat_canvas = tk.Canvas(self.chat_frame, bg=THEME.bg_secondary,
                                    highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.chat_frame, orient=tk.VERTICAL,
                                 command=self.chat_canvas.yview)
        
        self.messages_frame = tk.Frame(self.chat_canvas, bg=THEME.bg_secondary)
        
        self.chat_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.canvas_window = self.chat_canvas.create_window(
            (0, 0), window=self.messages_frame, anchor=tk.NW
        )
        
        self.messages_frame.bind("<Configure>", self._on_messages_configure)
        self.chat_canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Input area
        input_frame = tk.Frame(panel, bg=THEME.bg_secondary)
        input_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        # Input field
        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(input_frame, textvariable=self.input_var,
                                   font=("SF Pro Display", 13),
                                   bg=THEME.bg_input, fg=THEME.text_primary,
                                   insertbackground=THEME.text_primary,
                                   relief=tk.FLAT, bd=12)
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
        self.input_entry.bind("<Return>", self._on_enter)
        
        # Send button
        send_btn = tk.Button(input_frame, text="Send →",
                            command=self._on_send,
                            font=("SF Pro Display", 12, "bold"),
                            bg=THEME.accent_start, fg=THEME.text_primary,
                            activebackground=THEME.accent_hover,
                            relief=tk.FLAT, cursor="hand2",
                            padx=20, pady=10)
        send_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Welcome message
        self._add_message("Hello! I'm your macOS AI Agent. I can control your Mac using voice or text commands. Try saying 'turn on WiFi' or 'open Safari'.", False)
    
    def _create_status_panel(self, parent):
        """Create status and progress panel"""
        panel = tk.Frame(parent, bg=THEME.bg_tertiary, width=250)
        panel.pack(side=tk.RIGHT, fill=tk.Y)
        panel.pack_propagate(False)
        
        # Progress section
        tk.Label(panel, text="Task Progress",
                font=("SF Pro Display", 14, "bold"),
                bg=THEME.bg_tertiary, fg=THEME.text_primary).pack(pady=(20, 15), padx=15, anchor=tk.W)
        
        # Progress ring
        self.progress_ring = ProgressRing(panel, size=80, thickness=6)
        self.progress_ring.pack(pady=10)
        
        # Step info
        self.step_label = tk.Label(panel, text="No active task",
                                  font=("SF Pro Display", 11),
                                  bg=THEME.bg_tertiary, fg=THEME.text_secondary)
        self.step_label.pack(pady=5)
        
        # Separator
        tk.Frame(panel, bg=THEME.border, height=1).pack(fill=tk.X, padx=15, pady=20)
        
        # Activity log
        tk.Label(panel, text="Activity Log",
                font=("SF Pro Display", 14, "bold"),
                bg=THEME.bg_tertiary, fg=THEME.text_primary).pack(padx=15, anchor=tk.W)
        
        # Log text
        self.log_text = tk.Text(panel, font=("SF Mono", 10),
                               bg=THEME.bg_input, fg=THEME.text_secondary,
                               height=15, wrap=tk.WORD, relief=tk.FLAT,
                               padx=10, pady=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=(10, 20))
        self.log_text.configure(state=tk.DISABLED)
        
        # Stats section
        tk.Label(panel, text="Session Stats",
                font=("SF Pro Display", 12, "bold"),
                bg=THEME.bg_tertiary, fg=THEME.text_secondary).pack(padx=15, anchor=tk.W)
        
        stats_frame = tk.Frame(panel, bg=THEME.bg_tertiary)
        stats_frame.pack(fill=tk.X, padx=15, pady=10)
        
        self.stats_labels = {}
        for stat, value in [("Commands", "0"), ("Success", "0%"), ("Uptime", "0m")]:
            row = tk.Frame(stats_frame, bg=THEME.bg_tertiary)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=stat, font=("SF Pro Display", 10),
                    bg=THEME.bg_tertiary, fg=THEME.text_muted).pack(side=tk.LEFT)
            lbl = tk.Label(row, text=value, font=("SF Pro Display", 10, "bold"),
                          bg=THEME.bg_tertiary, fg=THEME.text_primary)
            lbl.pack(side=tk.RIGHT)
            self.stats_labels[stat.lower()] = lbl
    
    # =========================================================================
    # Chat functionality
    # =========================================================================
    
    def _add_message(self, text: str, is_user: bool):
        """Add a message to the chat"""
        bubble = MessageBubble(self.messages_frame, text, is_user)
        bubble.pack(fill=tk.X, pady=3)
        
        # Scroll to bottom
        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)
    
    def _on_messages_configure(self, event):
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        self.chat_canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _on_enter(self, event):
        self._on_send()
    
    def _on_send(self):
        """Handle send button click"""
        text = self.input_var.get().strip()
        if not text or self.is_processing:
            return
        
        self.input_var.set("")
        self._add_message(text, True)
        self._process_command(text)
    
    def _process_command(self, text: str):
        """Process a command in a background thread"""
        self.is_processing = True
        self._update_status("thinking", "Processing...")
        
        def run():
            try:
                if self.orchestrator:
                    result = self.orchestrator.execute_task(text)
                    self._queue_message("response", result.message)
                else:
                    # Demo mode - try direct command
                    if AGENT_AVAILABLE:
                        result = command_registry.execute(text)
                        if result:
                            self._queue_message("response", result.message)
                        else:
                            self._queue_message("response", f"Demo mode: Would execute '{text}'")
                    else:
                        self._queue_message("response", f"Demo mode: '{text}'")
            except Exception as e:
                self._queue_message("error", str(e))
            finally:
                self.is_processing = False
                self._queue_message("status_update", ("idle", "Ready"))
        
        threading.Thread(target=run, daemon=True).start()
    
    def _quick_command(self, cmd: str):
        """Execute a quick command"""
        self._add_message(cmd, True)
        self._process_command(cmd)
    
    def _start_voice(self):
        """Start voice recognition"""
        if self.voice and self.voice.is_available():
            self._update_status("listening", "Listening...")
            self._log("🎤 Listening for voice command...")
            
            def listen():
                text = self.voice.listen_once()
                if text:
                    self._queue_message("voice_input", text)
                else:
                    self._queue_message("status_update", ("idle", "Ready"))
            
            threading.Thread(target=listen, daemon=True).start()
        else:
            self._add_message("Voice recognition not available. Please type your command.", False)
    
    # =========================================================================
    # Event Handlers
    # =========================================================================
    
    def _on_task_started(self, event):
        self._queue_message("log", "▶ Task started")
        self._queue_message("status_update", ("executing", "Executing..."))
    
    def _on_task_completed(self, event):
        self._queue_message("log", "✓ Task completed")
        self._queue_message("status_update", ("success", "Completed"))
        self._queue_message("progress", 100)
    
    def _on_task_failed(self, event):
        error = event.data.get("error", "Unknown error")
        self._queue_message("log", f"✗ Task failed: {error}")
        self._queue_message("status_update", ("error", "Failed"))
    
    def _on_step_started(self, event):
        step = event.data.get("step", 0)
        desc = event.data.get("description", "")
        self._queue_message("log", f"→ Step {step}: {desc}")
        self.current_step = step
        if self.total_steps > 0:
            progress = (step / self.total_steps) * 100
            self._queue_message("progress", progress)
    
    def _on_step_completed(self, event):
        step = event.data.get("step", 0)
        self._queue_message("log", f"  ✓ Step {step} done")
    
    def _on_speak(self, text: str):
        """Handle agent speech"""
        self._queue_message("response", text)
    
    def _on_status(self, state: str, message: str):
        """Handle status updates"""
        self._queue_message("status_update", (state, message))
    
    # =========================================================================
    # UI Updates
    # =========================================================================
    
    def _queue_message(self, msg_type: str, data: Any):
        """Queue a message for UI update"""
        self.msg_queue.put((msg_type, data))
    
    def _process_messages(self):
        """Process queued messages (runs on main thread)"""
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()
                
                if msg_type == "response":
                    self._add_message(data, False)
                elif msg_type == "voice_input":
                    self._add_message(data, True)
                    self._process_command(data)
                elif msg_type == "log":
                    self._log(data)
                elif msg_type == "status_update":
                    state, message = data
                    self._update_status(state, message)
                elif msg_type == "progress":
                    self.progress_ring.set_progress(data)
                elif msg_type == "system":
                    self._log(f"ℹ {data}")
                elif msg_type == "error":
                    self._add_message(f"Error: {data}", False)
                    self._log(f"✗ {data}")
                elif msg_type == "warning":
                    self._log(f"⚠ {data}")
                    
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self._process_messages)
    
    def _update_status(self, state: str, message: str):
        """Update status indicator and label"""
        self.status_indicator.set_status(state)
        self.status_label.configure(text=message)
    
    def _log(self, text: str):
        """Add entry to activity log"""
        self.log_text.configure(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {text}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
    
    def run(self):
        """Start the application"""
        self.root.mainloop()


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Launch the modern GUI"""
    app = ModernAgentGUI()
    app.run()


if __name__ == "__main__":
    main()
