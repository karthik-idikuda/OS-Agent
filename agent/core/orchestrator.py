"""
Orchestrator - Coordinates the entire agent workflow

Enhanced orchestrator with:
- Event-driven architecture via MessageBus
- Direct command execution for instant commands
- AI reasoning for complex task understanding
- Context management for conversation and state
- Improved error recovery and replanning
"""
import time
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .models import (
    Action, ActionType, Plan, Step, TaskStatus, TaskResult,
    ConversationMessage, MessageRole, TaskIntent, IntentType,
    Clarification, Suggestion, ActionResult, ExecutionContext
)
from .config import AgentConfig
from .message_bus import MessageBus, EventType, message_bus

from ..perception.vision import VisionAnalyzer
from ..perception.screenshot import ScreenCapture
from ..planner.task_planner import TaskPlanner
from ..executor.action_executor import ActionExecutor
from ..commands.command_registry import command_registry, CommandResult
from ..ai.reasoning import ReasoningEngine, reasoning_engine
from ..ai.context_manager import ContextManager, context_manager


logger = logging.getLogger(__name__)


class OrchestratorState(Enum):
    """Orchestrator states"""
    IDLE = "idle"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    WAITING_USER = "waiting_user"
    REPLANNING = "replanning"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class ExecutionResult:
    """Result of task execution"""
    success: bool
    message: str
    steps_completed: int
    steps_total: int
    final_state: OrchestratorState
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    needs_user_input: bool = False
    question: Optional[str] = None
    suggestions: List[Suggestion] = field(default_factory=list)
    duration_sec: float = 0.0
    was_direct_command: bool = False


class Orchestrator:
    """
    Main orchestrator that coordinates:
    1. Intent analysis and command matching
    2. Direct command execution (fast path)
    3. Task planning for complex operations
    4. Step-by-step execution with verification
    5. Error recovery and replanning
    6. User interaction (clarification, status updates)
    
    Uses event-driven architecture for loose coupling.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        speak_callback: Optional[Callable[[str], None]] = None,
        status_callback: Optional[Callable[[str, str], None]] = None
    ):
        """
        Initialize orchestrator.
        
        Args:
            config: Agent configuration
            speak_callback: Function to call for voice output
            status_callback: Function for status updates (state, message)
        """
        self.config = config or AgentConfig()
        self.speak_callback = speak_callback
        self.status_callback = status_callback
        
        # Initialize components
        self.screen = ScreenCapture()
        self.vision = VisionAnalyzer()
        self.planner = TaskPlanner()
        self.executor = ActionExecutor()
        self.reasoner = reasoning_engine
        self.context = context_manager
        self.bus = message_bus
        
        # State
        self.state = OrchestratorState.IDLE
        self.current_plan: Optional[Plan] = None
        self.current_step_index = 0
        self.execution_history: List[Dict[str, Any]] = []
        self.retry_count = 0
        self.max_retries = 3
        self.start_time: Optional[datetime] = None
        
        # Subscribe to events
        self._setup_event_handlers()
        
        logger.info("Orchestrator initialized with enhanced architecture")
    
    def _setup_event_handlers(self):
        """Set up event handlers for the message bus"""
        self.bus.subscribe(EventType.TASK_CANCELLED, self._on_task_cancelled)
    
    def _on_task_cancelled(self, event):
        """Handle task cancellation"""
        logger.info("Task cancelled by user")
        self.state = OrchestratorState.IDLE
        self.current_plan = None
    
    # =========================================================================
    # Public Interface
    # =========================================================================
    
    def execute_task(
        self,
        task: str,
        context: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute a user task from start to finish.
        
        This is the main entry point. It:
        1. Analyzes user intent
        2. Checks for direct command match
        3. Falls back to AI planning for complex tasks
        
        Args:
            task: Natural language task description
            context: Optional additional context
        
        Returns:
            ExecutionResult with details
        """
        self.start_time = datetime.now()
        self.state = OrchestratorState.ANALYZING
        self.execution_history = []
        self.retry_count = 0
        
        # Add to conversation
        self.context.add_user_message(task)
        self.bus.publish(EventType.TASK_RECEIVED, {"task": task}, "orchestrator")
        
        try:
            # Step 1: Try direct command (fast path - always works without LLM)
            direct_result = self._try_direct_command(task)
            if direct_result:
                return direct_result
            
            # Step 2: Check if LLM is available for complex tasks
            if not self.reasoner.is_llm_available:
                # No LLM - can only handle direct commands
                self.speak("I can only handle direct commands like 'turn on wifi', 'open safari', or 'mute'. For complex tasks, please configure an LLM.")
                return ExecutionResult(
                    success=False,
                    message="No LLM configured. Only direct commands are available.",
                    steps_completed=0,
                    steps_total=0,
                    final_state=OrchestratorState.IDLE,
                    outputs=[],
                    duration_sec=0
                )
            
            # Step 3: Analyze intent with AI (LLM available)
            self._update_status("analyzing", "Analyzing your request...")
            intent = self.reasoner.analyze_intent(
                task, 
                self.context.get_active_app()
            )
            
            # Step 4: Handle based on intent type
            if intent.is_direct_command and intent.matched_command:
                # Direct command found by reasoner
                result = command_registry.execute(task)
                if result and result.success:
                    return self._create_direct_result(result)
            
            if intent.type == IntentType.QUESTION:
                # User is asking a question, respond conversationally
                return self._handle_question(task)
            
            if intent.type == IntentType.CANCELLATION:
                return self._handle_cancellation()
            
            # Step 5: Complex task - needs planning
            return self._execute_complex_task(task, intent, context)
            
        except Exception as e:
            logger.error(f"Task execution error: {e}", exc_info=True)
            self.state = OrchestratorState.ERROR
            self.speak(f"I encountered an error: {str(e)}")
            self.bus.publish(EventType.TASK_FAILED, {"error": str(e)}, "orchestrator")
            
            return ExecutionResult(
                success=False,
                message=str(e),
                steps_completed=self.current_step_index,
                steps_total=len(self.current_plan.steps) if self.current_plan else 0,
                final_state=self.state,
                outputs=self.execution_history,
                duration_sec=self._get_duration()
            )
    
    def provide_clarification(self, answer: str) -> ExecutionResult:
        """
        Process user's clarification answer and continue execution.
        
        Args:
            answer: User's response to clarification question
        
        Returns:
            ExecutionResult from continued execution
        """
        self.context.add_user_message(answer)
        
        # Check if it's a cancellation
        if self.reasoner.is_cancellation(answer):
            return self._handle_cancellation()
        
        # Answer pending clarification
        pending = self.context.get_pending_clarifications()
        if pending:
            self.context.answer_clarification(pending[0].id, answer)
        
        # Continue with the original task
        if self.current_plan:
            return self._continue_execution()
        
        return ExecutionResult(
            success=False,
            message="No active task to continue",
            steps_completed=0,
            steps_total=0,
            final_state=OrchestratorState.IDLE,
            outputs=[]
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status"""
        return {
            "state": self.state.value,
            "current_step": self.current_step_index,
            "total_steps": len(self.current_plan.steps) if self.current_plan else 0,
            "retry_count": self.retry_count,
            "plan_summary": self.current_plan.summary if self.current_plan else None,
            "duration_sec": self._get_duration(),
            "session_id": self.context.get_session_id()
        }
    
    def reset(self):
        """Reset orchestrator state"""
        self.state = OrchestratorState.IDLE
        self.current_plan = None
        self.current_step_index = 0
        self.execution_history = []
        self.retry_count = 0
        self.start_time = None
        self.context.clear_current_task()
        logger.info("Orchestrator reset")
    
    # =========================================================================
    # Direct Command Handling
    # =========================================================================
    
    def _try_direct_command(self, task: str) -> Optional[ExecutionResult]:
        """
        Try to execute task as a direct command.
        
        Returns ExecutionResult if matched, None otherwise.
        """
        result = command_registry.execute(task)
        
        if result:
            if result.success:
                self.speak(result.message)
                self.context.add_assistant_message(result.message)
                self.bus.publish(
                    EventType.TASK_COMPLETED,
                    {"task": task, "result": result.message},
                    "orchestrator"
                )
                return self._create_direct_result(result)
            else:
                # Command matched but failed
                logger.warning(f"Direct command failed: {result.error}")
        
        return None
    
    def _create_direct_result(self, result: CommandResult) -> ExecutionResult:
        """Create ExecutionResult from CommandResult"""
        self.state = OrchestratorState.COMPLETED
        return ExecutionResult(
            success=result.success,
            message=result.message,
            steps_completed=1,
            steps_total=1,
            final_state=self.state,
            outputs=[{"command_output": result.output}],
            was_direct_command=True,
            duration_sec=self._get_duration()
        )
    
    # =========================================================================
    # Complex Task Execution
    # =========================================================================
    
    def _execute_complex_task(
        self,
        task: str,
        intent: TaskIntent,
        context: Optional[str] = None
    ) -> ExecutionResult:
        """Execute a complex multi-step task"""
        
        # Check if clarification is needed
        clarifications = self.reasoner.generate_clarifications(task)
        if clarifications:
            self.state = OrchestratorState.WAITING_USER
            clarification = clarifications[0]
            self.context.add_clarification(clarification)
            self.speak(clarification.question)
            
            return ExecutionResult(
                success=False,
                message="Need clarification",
                steps_completed=0,
                steps_total=0,
                final_state=self.state,
                outputs=[],
                needs_user_input=True,
                question=clarification.question,
                duration_sec=self._get_duration()
            )
        
        # Get screen context
        self.state = OrchestratorState.PLANNING
        self._update_status("planning", "Analyzing the screen...")
        self.speak("Let me analyze the screen and plan the steps...")
        
        screen_context = self._get_screen_context()
        
        # Create plan
        self._update_status("planning", "Planning the steps...")
        plan_result = self._create_plan(task, screen_context, context)
        
        if not plan_result.get("success"):
            error = plan_result.get("error", "Failed to create plan")
            
            # Generate suggestions
            suggestions = self.reasoner.suggest_alternatives(task, error)
            
            return ExecutionResult(
                success=False,
                message=error,
                steps_completed=0,
                steps_total=0,
                final_state=OrchestratorState.ERROR,
                outputs=[],
                suggestions=suggestions,
                duration_sec=self._get_duration()
            )
        
        # Execute the plan
        self.context.set_current_task(task, self.current_plan)
        self.bus.publish(EventType.TASK_STARTED, {"task": task}, "orchestrator")
        self.speak(f"I'll complete this in {len(self.current_plan.steps)} steps.")
        
        return self._execute_plan()
    
    def _get_screen_context(self) -> str:
        """Get current screen context using vision"""
        try:
            capture = self.screen.capture()
            if capture.get("filepath"):
                analysis = self.vision.analyze_screen(capture.get("filepath"))
                self.context.update_screen_analysis(analysis)
                return analysis.summary if hasattr(analysis, 'summary') else str(analysis)
        except Exception as e:
            logger.warning(f"Screen context error: {e}")
        return "Screen context unavailable"
    
    def _create_plan(
        self,
        task: str,
        screen_context: str,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create execution plan"""
        # Build context
        context_parts = [f"Current screen: {screen_context}"]
        if additional_context:
            context_parts.append(f"Additional info: {additional_context}")
        
        # Add conversation context
        history = self.context.get_conversation_text(3)
        if history:
            context_parts.append(f"Recent conversation:\n{history}")
        
        # Create plan
        context_dict = {"screen": screen_context, "history": history}
        self.current_plan = self.planner.create_plan(task, context_dict)
        self.current_step_index = 0
        
        if self.current_plan and self.current_plan.steps:
            self.bus.publish(
                EventType.PLAN_CREATED,
                {"plan_id": self.current_plan.id, "steps": len(self.current_plan.steps)},
                "orchestrator"
            )
            return {"success": True}
        else:
            return {"success": False, "error": "Could not create a valid plan"}
    
    def _execute_plan(self) -> ExecutionResult:
        """Execute the current plan step by step"""
        self.state = OrchestratorState.EXECUTING
        
        if not self.current_plan:
            return ExecutionResult(
                success=False,
                message="No plan to execute",
                steps_completed=0,
                steps_total=0,
                final_state=OrchestratorState.ERROR,
                outputs=[],
                duration_sec=self._get_duration()
            )
        
        total_steps = len(self.current_plan.steps)
        
        while self.current_step_index < total_steps:
            step = self.current_plan.steps[self.current_step_index]
            
            # Publish step start event
            self.bus.publish(
                EventType.STEP_STARTED,
                {"step": self.current_step_index + 1, "description": step.description},
                "orchestrator"
            )
            
            # Announce step
            self._update_status("executing", f"Step {self.current_step_index + 1}: {step.description}")
            self.speak(f"Step {self.current_step_index + 1}: {step.description}")
            
            # Execute step
            step_result = self._execute_step(step)
            self.execution_history.append({
                "step_index": self.current_step_index,
                "step": step.description,
                "result": step_result
            })
            
            # Handle user input request
            if step_result.get("needs_input"):
                self.state = OrchestratorState.WAITING_USER
                question = step_result.get("question", "I need more information")
                self.speak(question)
                
                return ExecutionResult(
                    success=False,
                    message="Waiting for user input",
                    steps_completed=self.current_step_index,
                    steps_total=total_steps,
                    final_state=self.state,
                    outputs=self.execution_history,
                    needs_user_input=True,
                    question=question,
                    duration_sec=self._get_duration()
                )
            
            # Check success
            if step_result.get("success"):
                self.bus.publish(
                    EventType.STEP_COMPLETED,
                    {"step": self.current_step_index + 1},
                    "orchestrator"
                )
                self.current_step_index += 1
                self.retry_count = 0
                self.context.update_step_index(self.current_step_index)
                
                # Verify if needed
                if step.verify:
                    self.state = OrchestratorState.VERIFYING
                    verified = self._verify_step(step)
                    
                    if not verified:
                        self.speak("That didn't work as expected. Trying another approach...")
                        replan_success = self._handle_failure(step, "Verification failed")
                        
                        if not replan_success:
                            suggestions = self.reasoner.suggest_alternatives(
                                self.context.get_current_task() or "",
                                "Verification failed",
                                step.description
                            )
                            return ExecutionResult(
                                success=False,
                                message="Step verification failed",
                                steps_completed=self.current_step_index,
                                steps_total=total_steps,
                                final_state=OrchestratorState.ERROR,
                                outputs=self.execution_history,
                                suggestions=suggestions,
                                duration_sec=self._get_duration()
                            )
            else:
                # Step failed
                error = step_result.get("error", "Unknown error")
                self.bus.publish(
                    EventType.STEP_FAILED,
                    {"step": self.current_step_index + 1, "error": error},
                    "orchestrator"
                )
                logger.warning(f"Step failed: {error}")
                
                replan_success = self._handle_failure(step, error)
                if not replan_success:
                    self.speak(f"I couldn't complete step {self.current_step_index + 1}.")
                    suggestions = self.reasoner.suggest_alternatives(
                        self.context.get_current_task() or "",
                        error,
                        step.description
                    )
                    return ExecutionResult(
                        success=False,
                        message=f"Step failed: {error}",
                        steps_completed=self.current_step_index,
                        steps_total=total_steps,
                        final_state=OrchestratorState.ERROR,
                        outputs=self.execution_history,
                        suggestions=suggestions,
                        duration_sec=self._get_duration()
                    )
            
            # Small delay between steps
            time.sleep(0.3)
        
        # All steps completed
        self.state = OrchestratorState.COMPLETED
        self.bus.publish(EventType.TASK_COMPLETED, {}, "orchestrator")
        self.speak("Task completed successfully!")
        self.context.add_assistant_message("Task completed successfully.")
        
        return ExecutionResult(
            success=True,
            message="All steps completed",
            steps_completed=total_steps,
            steps_total=total_steps,
            final_state=self.state,
            outputs=self.execution_history,
            duration_sec=self._get_duration()
        )
    
    def _continue_execution(self) -> ExecutionResult:
        """Continue execution after clarification"""
        if self.current_plan:
            return self._execute_plan()
        
        return ExecutionResult(
            success=False,
            message="No plan to continue",
            steps_completed=0,
            steps_total=0,
            final_state=OrchestratorState.ERROR,
            outputs=[],
            duration_sec=self._get_duration()
        )
    
    def _execute_step(self, step: Step) -> Dict[str, Any]:
        """Execute a single step with all its actions"""
        results = []
        
        for action in step.actions:
            self.bus.publish(
                EventType.ACTION_STARTED,
                {"action": action.type.value, "description": action.description},
                "orchestrator"
            )
            
            result = self.executor.execute(action, self.vision)
            results.append(result)
            
            if result.get("success"):
                self.bus.publish(EventType.ACTION_COMPLETED, {}, "orchestrator")
                
                # Cache found elements
                if action.type == ActionType.FIND_ELEMENT and result.get("element"):
                    elem = result["element"]
                    self.context.cache_element(
                        action.params.get("target", "element"),
                        elem.get("x", 0),
                        elem.get("y", 0)
                    )
            else:
                self.bus.publish(
                    EventType.ACTION_FAILED,
                    {"error": result.get("error")},
                    "orchestrator"
                )
                return result
            
            # If action needs user input
            if result.get("needs_input"):
                return result
            
            # Small delay between actions
            time.sleep(0.2)
        
        return {"success": True, "outputs": results}
    
    def _verify_step(self, step: Step) -> bool:
        """Verify a step completed correctly"""
        if not step.verify:
            return True
        
        try:
            capture = self.screen.capture()
            result = self.vision.verify_action(step.verify)
            
            verified = result.get("verified", False)
            
            if verified:
                self.bus.publish(EventType.VERIFICATION_PASSED, {}, "orchestrator")
            else:
                self.bus.publish(EventType.VERIFICATION_FAILED, {}, "orchestrator")
            
            return verified
        except Exception as e:
            logger.warning(f"Verification error: {e}")
            return True  # Assume success if verification fails
    
    def _handle_failure(self, failed_step: Step, error: str) -> bool:
        """Handle step failure with retry and replan"""
        self.retry_count += 1
        
        if self.retry_count > self.max_retries:
            self.speak("I've tried multiple times but can't complete this step.")
            return False
        
        self.state = OrchestratorState.REPLANNING
        self.bus.publish(EventType.STEP_RETRYING, {"attempt": self.retry_count}, "orchestrator")
        
        # Get fresh screen context
        screen_context = self._get_screen_context()
        
        # Replan
        remaining_task = self._get_remaining_task()
        context = {
            "screen": screen_context,
            "error": error,
            "failed_step": failed_step.description,
            "retry": self.retry_count
        }
        
        new_plan = self.planner.replan(remaining_task, failed_step, error, context)
        
        if new_plan and new_plan.steps:
            # Replace remaining steps
            completed_steps = self.current_plan.steps[:self.current_step_index]
            self.current_plan.steps = completed_steps + new_plan.steps
            self.state = OrchestratorState.EXECUTING
            self.bus.publish(EventType.PLAN_UPDATED, {}, "orchestrator")
            return True
        
        return False
    
    def _get_remaining_task(self) -> str:
        """Get description of remaining work"""
        if not self.current_plan:
            return ""
        
        remaining = self.current_plan.steps[self.current_step_index:]
        descriptions = [s.description for s in remaining]
        return "Complete: " + "; ".join(descriptions)
    
    # =========================================================================
    # Special Handlers
    # =========================================================================
    
    def _handle_question(self, question: str) -> ExecutionResult:
        """Handle user asking a question"""
        # Simple response for now - can be enhanced with RAG
        response = "I can help you control your Mac. Try commands like 'open Safari', 'turn on WiFi', or more complex tasks like 'send a message on WhatsApp'."
        
        self.speak(response)
        self.context.add_assistant_message(response)
        self.state = OrchestratorState.IDLE
        
        return ExecutionResult(
            success=True,
            message=response,
            steps_completed=0,
            steps_total=0,
            final_state=self.state,
            outputs=[],
            duration_sec=self._get_duration()
        )
    
    def _handle_cancellation(self) -> ExecutionResult:
        """Handle task cancellation"""
        self.speak("Okay, I've cancelled the current task.")
        self.context.add_assistant_message("Task cancelled.")
        self.bus.publish(EventType.TASK_CANCELLED, {}, "orchestrator")
        
        self.reset()
        
        return ExecutionResult(
            success=True,
            message="Task cancelled",
            steps_completed=self.current_step_index,
            steps_total=len(self.current_plan.steps) if self.current_plan else 0,
            final_state=OrchestratorState.IDLE,
            outputs=self.execution_history,
            duration_sec=self._get_duration()
        )
    
    # =========================================================================
    # Helpers
    # =========================================================================
    
    def speak(self, message: str):
        """Speak a message to the user"""
        logger.info(f"[AGENT] {message}")
        if self.speak_callback:
            self.speak_callback(message)
    
    def _update_status(self, state: str, message: str):
        """Update status via callback"""
        if self.status_callback:
            self.status_callback(state, message)
    
    def _get_duration(self) -> float:
        """Get execution duration in seconds"""
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0

