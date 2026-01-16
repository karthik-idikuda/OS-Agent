#!/usr/bin/env python3
"""
macOS AI Agent - Main Entry Point

A voice-controlled, fully autonomous macOS agent.
Uses Llama for planning and LLaVA for vision.

Usage:
    python run_agent.py              # Interactive CLI mode
    python run_agent.py --voice      # Voice-controlled mode
    python run_agent.py --task "..."  # Execute single task
"""
import asyncio
import argparse
import sys
import signal
from typing import Optional

from agent.core import Orchestrator, AgentConfig
from agent.voice import VoiceInterface, VoiceConfig
from agent.utils import setup_logging, ActionLogger


# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_banner():
    """Print startup banner"""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🤖 macOS AI Agent                                          ║
║   Voice-controlled computer automation                        ║
║                                                               ║
║   Models: Llama 3.2 (Planning) + LLaVA (Vision)              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
{Colors.RESET}
"""
    print(banner)


def print_help():
    """Print help message"""
    help_text = f"""
{Colors.YELLOW}Available Commands:{Colors.RESET}
  • Type any task in natural language
  • "help" - Show this help
  • "status" - Show agent status
  • "screenshot" - Take a screenshot
  • "exit" or "quit" - Exit the agent

{Colors.YELLOW}Example Tasks:{Colors.RESET}
  • "Open Safari and go to google.com"
  • "Turn on WiFi"
  • "Set volume to 50%"
  • "Open WhatsApp and send hello to John"
  • "Find the Settings icon and click it"
  • "Take a screenshot"

{Colors.YELLOW}Direct Commands:{Colors.RESET}
  • wifi on/off     • bluetooth on/off
  • volume up/down  • brightness up/down
  • mute/unmute     • dark mode on/off
"""
    print(help_text)


class AgentCLI:
    """Command-line interface for the agent"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.orchestrator = Orchestrator(
            config=config,
            speak_callback=self._on_speak
        )
        self.action_logger = ActionLogger()
        self.running = True
    
    def _on_speak(self, message: str):
        """Handle agent speech output"""
        print(f"{Colors.GREEN}[Agent]{Colors.RESET} {message}")
    
    async def run_task(self, task: str) -> bool:
        """Run a single task"""
        self.action_logger.log_task_start(task)
        
        print(f"\n{Colors.BLUE}[Task]{Colors.RESET} {task}")
        print(f"{Colors.CYAN}{'─' * 50}{Colors.RESET}")
        
        result = await self.orchestrator.execute_task(task)
        
        self.action_logger.log_task_end(task, result.success)
        
        if result.needs_user_input:
            # Agent needs clarification
            print(f"\n{Colors.YELLOW}[Question]{Colors.RESET} {result.question}")
            answer = input(f"{Colors.CYAN}Your answer: {Colors.RESET}")
            self.orchestrator.provide_clarification(answer)
            # Continue with the clarification
            return await self.run_task(f"Continue with: {answer}")
        
        if result.success:
            print(f"\n{Colors.GREEN}✓ Task completed!{Colors.RESET}")
            print(f"  Steps: {result.steps_completed}/{result.steps_total}")
        else:
            print(f"\n{Colors.RED}✗ Task failed:{Colors.RESET} {result.message}")
        
        return result.success
    
    def _handle_special_command(self, cmd: str) -> bool:
        """
        Handle special commands.
        Returns True if command was handled.
        """
        cmd_lower = cmd.lower().strip()
        
        if cmd_lower in ["exit", "quit", "q"]:
            self.running = False
            print(f"{Colors.YELLOW}Goodbye!{Colors.RESET}")
            return True
        
        if cmd_lower == "help":
            print_help()
            return True
        
        if cmd_lower == "status":
            status = self.orchestrator.get_status()
            print(f"\n{Colors.CYAN}Agent Status:{Colors.RESET}")
            print(f"  State: {status['state']}")
            print(f"  Current step: {status['current_step']}/{status['total_steps']}")
            return True
        
        return False
    
    async def interactive_loop(self):
        """Run interactive CLI loop"""
        print_banner()
        print_help()
        
        print(f"{Colors.CYAN}Agent ready. Type a task or 'help' for commands.{Colors.RESET}\n")
        
        while self.running:
            try:
                user_input = input(f"{Colors.BOLD}You: {Colors.RESET}").strip()
                
                if not user_input:
                    continue
                
                # Check for special commands
                if self._handle_special_command(user_input):
                    continue
                
                # Run the task
                await self.run_task(user_input)
                print()
                
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}Interrupted. Goodbye!{Colors.RESET}")
                break
            except EOFError:
                break
            except Exception as e:
                print(f"{Colors.RED}Error: {e}{Colors.RESET}")


class AgentVoice:
    """Voice-controlled interface for the agent"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.voice = VoiceInterface(VoiceConfig(
            wake_word="hey computer",
            language="en-US"
        ))
        self.orchestrator = Orchestrator(
            config=config,
            speak_callback=self._on_speak
        )
        self.running = True
    
    def _on_speak(self, message: str):
        """Handle agent speech output"""
        print(f"{Colors.GREEN}[Agent]{Colors.RESET} {message}")
        self.voice.speak(message)
    
    async def _process_command(self, command: str):
        """Process a voice command"""
        if not command:
            return
        
        print(f"\n{Colors.BLUE}[You said]{Colors.RESET} {command}")
        
        # Check for exit commands
        if any(word in command.lower() for word in ["stop", "exit", "quit", "goodbye"]):
            self.voice.speak("Goodbye!")
            self.running = False
            return
        
        # Run the task
        result = await self.orchestrator.execute_task(command)
        
        if result.needs_user_input:
            self.voice.speak(result.question)
            answer = self.voice.listen_once(timeout=10)
            if answer:
                self.orchestrator.provide_clarification(answer)
    
    async def run(self):
        """Run voice-controlled agent"""
        print_banner()
        
        if not self.voice.is_available():
            print(f"{Colors.RED}Voice interface not available.{Colors.RESET}")
            print("Install requirements: pip install SpeechRecognition edge-tts pyaudio")
            return
        
        print(f"{Colors.CYAN}Voice mode active!{Colors.RESET}")
        print(f"Say '{self.voice.config.wake_word}' to wake me up.")
        print("Press Ctrl+C to exit.\n")
        
        self.voice.speak("Ready. Say hey computer to wake me up.")
        
        while self.running:
            try:
                # Wait for wake word
                print(f"{Colors.YELLOW}Waiting for wake word...{Colors.RESET}")
                if self.voice.listen_for_wake_word(timeout=30):
                    self.voice.play_sound("listening")
                    self.voice.speak("Yes?")
                    
                    # Listen for command
                    command = self.voice.listen_once(timeout=10)
                    if command:
                        await self._process_command(command)
                    else:
                        self.voice.speak("I didn't catch that.")
                        
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}Goodbye!{Colors.RESET}")
                break


def check_requirements():
    """Check if required tools are available"""
    issues = []
    
    # Check Ollama
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code != 200:
            issues.append("Ollama not responding")
    except:
        issues.append("Ollama not running. Start with: ollama serve")
    
    # Check PyAutoGUI
    try:
        import pyautogui
    except ImportError:
        issues.append("PyAutoGUI not installed: pip install pyautogui")
    
    return issues


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="macOS AI Agent - Voice-controlled computer automation"
    )
    parser.add_argument(
        "--voice", "-v",
        action="store_true",
        help="Enable voice control mode"
    )
    parser.add_argument(
        "--task", "-t",
        type=str,
        help="Execute a single task and exit"
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    import logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level=log_level)
    
    # Check requirements
    issues = check_requirements()
    if issues:
        print(f"{Colors.RED}Missing requirements:{Colors.RESET}")
        for issue in issues:
            print(f"  • {issue}")
        print()
        # Continue anyway, some features might still work
    
    # Create config
    config = AgentConfig()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print(f"\n{Colors.YELLOW}Shutting down...{Colors.RESET}")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run appropriate mode
    if args.task:
        # Single task mode
        cli = AgentCLI(config)
        asyncio.run(cli.run_task(args.task))
    elif args.voice:
        # Voice mode
        agent = AgentVoice(config)
        asyncio.run(agent.run())
    else:
        # Interactive CLI mode
        cli = AgentCLI(config)
        asyncio.run(cli.interactive_loop())


if __name__ == "__main__":
    main()
