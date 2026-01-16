"""
Data models for the Voice Agent

Enhanced models for the professional AI agent with:
- ActionResult for detailed execution outcomes
- ExecutionContext for state tracking
- Suggestion and Clarification for AI interactions
- TaskIntent for intent classification
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum, auto
from datetime import datetime
import uuid


# =============================================================================
# ENUMS
# =============================================================================

class ActionType(Enum):
    """Types of actions the agent can perform"""
    # Mouse actions
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    MOVE_TO = "move_to"
    DRAG = "drag"
    SCROLL = "scroll"
    
    # Keyboard actions
    TYPE = "type"
    PRESS_KEY = "press_key"
    HOTKEY = "hotkey"
    
    # System actions
    SYSTEM_COMMAND = "system_command"
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    OPEN_URL = "open_url"
    
    # Direct commands (no planning needed)
    DIRECT_COMMAND = "direct_command"
    
    # Agent actions
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    FIND_ELEMENT = "find_element"
    VERIFY = "verify"
    ASK_USER = "ask_user"
    DONE = "done"
    ERROR = "error"


class TaskStatus(Enum):
    """Status of a task"""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    WAITING_USER = "waiting_user"
    REPLANNING = "replanning"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageRole(Enum):
    """Role in conversation"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class IntentType(Enum):
    """Classification of user intent"""
    # Direct commands (instant execution)
    SYSTEM_CONTROL = "system_control"      # WiFi, Bluetooth, Volume, etc.
    APP_LAUNCH = "app_launch"              # Open specific app
    APP_CLOSE = "app_close"                # Close app
    NAVIGATION = "navigation"              # Go to URL, open file
    
    # Complex tasks (require planning)
    MULTI_STEP_TASK = "multi_step_task"    # Complex operations
    SEARCH_TASK = "search_task"            # Search for something
    COMMUNICATION = "communication"         # Send message, email
    
    # Conversational
    QUESTION = "question"                   # User asking something
    CLARIFICATION = "clarification"         # User providing info
    CONFIRMATION = "confirmation"           # Yes/No response
    CANCELLATION = "cancellation"           # Cancel current task
    
    # Unknown
    UNKNOWN = "unknown"


class Confidence(Enum):
    """Confidence levels for AI decisions"""
    HIGH = "high"        # > 0.8 - Proceed automatically
    MEDIUM = "medium"    # 0.5-0.8 - Might need confirmation
    LOW = "low"          # < 0.5 - Ask for clarification


class RecoveryStrategy(Enum):
    """Strategies for recovering from failures"""
    RETRY = "retry"                    # Try the same action again
    RETRY_ALTERNATIVE = "retry_alt"    # Try different approach
    SKIP = "skip"                      # Skip this step
    REPLAN = "replan"                  # Create new plan
    ASK_USER = "ask_user"              # Ask user for help
    ABORT = "abort"                    # Give up


# =============================================================================
# CORE ACTION MODELS
# =============================================================================

@dataclass
class Action:
    """Single action to execute"""
    type: ActionType
    description: str
    params: Dict[str, Any] = field(default_factory=dict)
    
    # Pre/post conditions
    preconditions: List[str] = field(default_factory=list)
    expected_result: Optional[str] = None
    
    # Execution state
    executed: bool = False
    success: bool = False
    result: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: int = 0
    
    # Retry info
    max_retries: int = 3
    retry_count: int = 0


@dataclass
class ActionResult:
    """Detailed result of action execution"""
    action: Action
    success: bool
    message: str
    
    # Details
    output: Any = None
    error: Optional[str] = None
    screenshot_path: Optional[str] = None
    
    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_ms: int = 0
    
    # For element finding
    element_found: bool = False
    element_coordinates: Optional[Tuple[int, int]] = None
    
    # Recovery
    needs_retry: bool = False
    suggested_recovery: Optional[RecoveryStrategy] = None
    
    @property
    def elapsed_time(self) -> float:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0


# =============================================================================
# PLANNING MODELS
# =============================================================================

@dataclass
class Step:
    """A step in the execution plan"""
    id: int
    description: str
    actions: List[Action] = field(default_factory=list)
    verify: Optional[str] = None             # What to verify after step
    
    # Dependencies
    depends_on: List[int] = field(default_factory=list)  # Step IDs
    can_parallel: bool = False               # Can run with other steps
    
    # Execution state
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    
    # Results
    result: Optional[ActionResult] = None
    verification_passed: bool = False


@dataclass
class Plan:
    """Execution plan for a task"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal: str = ""
    summary: str = ""
    steps: List[Step] = field(default_factory=list)
    
    # Clarifications
    clarifications_needed: List[str] = field(default_factory=list)
    clarifications_received: Dict[str, str] = field(default_factory=dict)
    
    # State
    current_step: int = 0
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # Metadata
    is_direct_command: bool = False          # Skip planning for direct commands
    estimated_duration_sec: int = 0
    
    @property
    def progress(self) -> float:
        """Return progress as 0.0 to 1.0"""
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.status == TaskStatus.COMPLETED)
        return completed / len(self.steps)
    
    @property
    def completed_steps(self) -> int:
        return sum(1 for s in self.steps if s.status == TaskStatus.COMPLETED)


# =============================================================================
# PERCEPTION MODELS
# =============================================================================

@dataclass
class ScreenElement:
    """UI element detected on screen"""
    text: str
    element_type: str                        # button, input, link, text, icon
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)  # (x, y, width, height)
    center: Tuple[int, int] = (0, 0)         # (x, y) center point
    confidence: float = 0.0
    
    # Additional info
    is_interactive: bool = True
    parent_element: Optional[str] = None
    accessibility_label: Optional[str] = None


@dataclass
class ScreenAnalysis:
    """Result of screen analysis"""
    screenshot_path: str
    width: int
    height: int
    summary: str                             # What's visible on screen
    elements: List[ScreenElement] = field(default_factory=list)
    active_app: Optional[str] = None
    active_window: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    # OCR text if extracted
    raw_text: Optional[str] = None
    
    # Analysis metadata
    analysis_time_ms: int = 0
    model_used: str = "llava:7b"


# =============================================================================
# CONVERSATION MODELS
# =============================================================================

@dataclass
class ConversationMessage:
    """A message in the conversation"""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Metadata
    intent: Optional[IntentType] = None
    entities: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Clarification:
    """A clarification question from the agent"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    question: str = ""
    context: str = ""                        # Why we're asking
    options: List[str] = field(default_factory=list)  # Suggested answers
    required: bool = True                    # Must answer to proceed
    
    # Response
    answered: bool = False
    answer: Optional[str] = None
    answered_at: Optional[datetime] = None


@dataclass
class Suggestion:
    """A suggestion from the agent"""
    text: str
    confidence: Confidence = Confidence.MEDIUM
    action: Optional[Action] = None          # Suggested action to take
    alternatives: List[str] = field(default_factory=list)


# =============================================================================
# INTENT & CONTEXT MODELS
# =============================================================================

@dataclass
class TaskIntent:
    """Parsed user intent"""
    type: IntentType
    raw_input: str
    confidence: float = 0.0
    
    # Extracted information
    target_app: Optional[str] = None
    target_url: Optional[str] = None
    target_element: Optional[str] = None
    action_verb: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Direct command matching
    matched_command: Optional[str] = None
    is_direct_command: bool = False
    
    # For multi-step tasks
    subtasks: List[str] = field(default_factory=list)


@dataclass
class ExecutionContext:
    """Current execution context for the agent"""
    # Current state
    current_task: Optional[str] = None
    current_plan: Optional[Plan] = None
    current_step_index: int = 0
    
    # Screen state
    last_screenshot: Optional[str] = None
    last_screen_analysis: Optional[ScreenAnalysis] = None
    
    # Conversation
    conversation_history: List[ConversationMessage] = field(default_factory=list)
    pending_clarifications: List[Clarification] = field(default_factory=list)
    
    # Element tracking
    last_found_element: Optional[Dict[str, Any]] = None
    element_cache: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    
    # Session info
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: datetime = field(default_factory=datetime.now)
    
    def add_message(self, role: MessageRole, content: str):
        """Add message to conversation history"""
        self.conversation_history.append(
            ConversationMessage(role=role, content=content)
        )
    
    def get_recent_history(self, n: int = 10) -> List[ConversationMessage]:
        """Get last n messages"""
        return self.conversation_history[-n:]
    
    def clear_element_cache(self):
        """Clear cached element positions"""
        self.element_cache.clear()


# =============================================================================
# RESULT MODELS
# =============================================================================

@dataclass
class TaskResult:
    """Result of task execution"""
    success: bool
    message: str
    steps_completed: int
    steps_total: int
    
    # Details
    screenshots: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_sec: float = 0.0
    
    # Suggestions for user
    suggestions: List[Suggestion] = field(default_factory=list)
    
    # For debugging
    plan_id: Optional[str] = None
    step_results: List[ActionResult] = field(default_factory=list)
