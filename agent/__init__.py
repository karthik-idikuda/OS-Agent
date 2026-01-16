"""
macOS AI Agent - Voice-controlled computer automation

A fully autonomous AI agent that can:
- Listen to voice commands
- Analyze screen using vision (LLaVA)
- Plan complex multi-step tasks (Llama)
- Execute actions (click, type, system commands)
- Verify results and replan if needed
- Ask clarifying questions when uncertain
- Execute direct commands instantly (WiFi, volume, etc.)
"""
from .core import (
    Orchestrator,
    AgentConfig,
    ActionType,
    OrchestratorState,
    ExecutionResult,
    TaskIntent,
    IntentType,
    message_bus,
    EventType
)
from .voice import VoiceInterface
from .perception import ScreenCapture, VisionAnalyzer
from .planner import TaskPlanner
from .executor import ActionExecutor
from .commands import CommandRegistry, command_registry
from .ai import ReasoningEngine, ContextManager
from .storage import AgentDatabase, ScreenshotCache

__version__ = "2.0.0"
__author__ = "macOS Agent Team"

__all__ = [
    # Core
    "Orchestrator",
    "AgentConfig",
    "ActionType",
    "OrchestratorState",
    "ExecutionResult",
    "TaskIntent",
    "IntentType",
    # Events
    "message_bus",
    "EventType",
    # Voice
    "VoiceInterface",
    # Perception
    "ScreenCapture",
    "VisionAnalyzer",
    # Planning
    "TaskPlanner",
    # Execution
    "ActionExecutor",
    # Commands
    "CommandRegistry",
    "command_registry",
    # AI
    "ReasoningEngine",
    "ContextManager",
    # Storage
    "AgentDatabase",
    "ScreenshotCache",
]

