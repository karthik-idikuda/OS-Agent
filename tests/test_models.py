"""
Unit Tests for Core Models
"""
import pytest
from agent.core.models import (
    ActionType, TaskStatus, IntentType, Confidence, RecoveryStrategy,
    Action, Step, Plan, ScreenElement, ScreenAnalysis,
    ConversationMessage, MessageRole,
    ActionResult, TaskIntent, Clarification, Suggestion, ExecutionContext
)


class TestActionType:
    """Tests for ActionType enum"""
    
    def test_mouse_actions(self):
        """Test mouse action types exist"""
        assert ActionType.CLICK.value == "click"
        assert ActionType.DOUBLE_CLICK.value == "double_click"
        assert ActionType.RIGHT_CLICK.value == "right_click"
        assert ActionType.DRAG.value == "drag"
    
    def test_keyboard_actions(self):
        """Test keyboard action types exist"""
        assert ActionType.TYPE.value == "type"
        assert ActionType.PRESS_KEY.value == "press_key"
        assert ActionType.HOTKEY.value == "hotkey"
    
    def test_system_actions(self):
        """Test system action types exist"""
        assert ActionType.SYSTEM_COMMAND.value == "system_command"
        assert ActionType.OPEN_APP.value == "open_app"
        assert ActionType.CLOSE_APP.value == "close_app"
        assert ActionType.OPEN_URL.value == "open_url"
    
    def test_agent_actions(self):
        """Test agent-specific action types exist"""
        assert ActionType.WAIT.value == "wait"
        assert ActionType.SCREENSHOT.value == "screenshot"
        assert ActionType.FIND_ELEMENT.value == "find_element"
        assert ActionType.VERIFY.value == "verify"


class TestTaskStatus:
    """Tests for TaskStatus enum"""
    
    def test_status_values(self):
        """Test all status values exist"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.PLANNING.value == "planning"
        assert TaskStatus.EXECUTING.value == "executing"
        assert TaskStatus.WAITING_USER.value == "waiting_user"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"


class TestIntentType:
    """Tests for IntentType enum"""
    
    def test_intent_types_exist(self):
        """Test all intent types exist"""
        expected = [
            "SYSTEM_CONTROL", "APP_LAUNCH", "APP_CLOSE", "NAVIGATION",
            "MULTI_STEP_TASK", "SEARCH_TASK", "COMMUNICATION",
            "QUESTION", "CLARIFICATION", "CONFIRMATION", "CANCELLATION", "UNKNOWN"
        ]
        
        for name in expected:
            assert hasattr(IntentType, name)


class TestAction:
    """Tests for Action dataclass"""
    
    def test_action_creation(self):
        """Test Action creation"""
        action = Action(
            type=ActionType.CLICK,
            description="Click at coordinates",
            params={"x": 100, "y": 200}
        )
        
        assert action.type == ActionType.CLICK
        assert action.params["x"] == 100
        assert action.params["y"] == 200
        assert action.description == "Click at coordinates"
    
    def test_action_default_values(self):
        """Test Action default values"""
        action = Action(type=ActionType.WAIT, description="Wait for loading")
        
        assert action.params == {}
        assert action.executed == False
        assert action.success == False


class TestStep:
    """Tests for Step dataclass"""
    
    def test_step_creation(self):
        """Test Step creation"""
        action = Action(type=ActionType.CLICK, description="Click", params={"x": 100, "y": 100})
        step = Step(
            id=1,
            description="Click button",
            actions=[action],
            verify="Button clicked"
        )
        
        assert step.id == 1
        assert step.description == "Click button"
        assert len(step.actions) == 1
        assert step.verify == "Button clicked"
        assert step.status == TaskStatus.PENDING  # Default
    
    def test_step_multiple_actions(self):
        """Test step with multiple actions"""
        actions = [
            Action(type=ActionType.CLICK, description="Click", params={}),
            Action(type=ActionType.TYPE, description="Type", params={"text": "hello"}),
            Action(type=ActionType.PRESS_KEY, description="Press", params={"key": "enter"})
        ]
        
        step = Step(id=1, description="Fill form", actions=actions)
        assert len(step.actions) == 3


class TestPlan:
    """Tests for Plan dataclass"""
    
    def test_plan_creation(self):
        """Test Plan creation"""
        steps = [
            Step(id=1, description="Step 1", actions=[]),
            Step(id=2, description="Step 2", actions=[])
        ]
        
        plan = Plan(goal="Test task", steps=steps, summary="Test plan")
        
        assert plan.goal == "Test task"
        assert len(plan.steps) == 2
        assert plan.summary == "Test plan"
    
    def test_plan_with_completed_steps(self):
        """Test plan with completed steps"""
        steps = [
            Step(id=1, description="Step 1", actions=[], status=TaskStatus.COMPLETED),
            Step(id=2, description="Step 2", actions=[], status=TaskStatus.EXECUTING),
            Step(id=3, description="Step 3", actions=[], status=TaskStatus.PENDING)
        ]
        
        plan = Plan(goal="Test", steps=steps)
        
        # Check we can count completed steps
        completed = sum(1 for s in plan.steps if s.status == TaskStatus.COMPLETED)
        assert completed == 1


class TestScreenElement:
    """Tests for ScreenElement dataclass"""
    
    def test_element_creation(self):
        """Test ScreenElement creation"""
        element = ScreenElement(
            text="Submit",
            element_type="button",
            bbox=(100, 200, 80, 30),
            center=(140, 215),
            confidence=0.95
        )
        
        assert element.element_type == "button"
        assert element.text == "Submit"
        assert element.bbox == (100, 200, 80, 30)
        assert element.center == (140, 215)
        assert element.confidence == 0.95


class TestScreenAnalysis:
    """Tests for ScreenAnalysis dataclass"""
    
    def test_analysis_creation(self):
        """Test ScreenAnalysis creation"""
        elements = [
            ScreenElement(text="OK", element_type="button", center=(100, 100)),
            ScreenElement(text="", element_type="input", center=(200, 100))
        ]
        
        analysis = ScreenAnalysis(
            screenshot_path="/tmp/test.png",
            width=1440,
            height=900,
            summary="Login page with form",
            elements=elements,
            active_app="Safari"
        )
        
        assert analysis.summary == "Login page with form"
        assert len(analysis.elements) == 2
        assert analysis.active_app == "Safari"
        assert analysis.screenshot_path == "/tmp/test.png"


class TestConversationMessage:
    """Tests for ConversationMessage dataclass"""
    
    def test_message_creation(self):
        """Test message creation"""
        msg = ConversationMessage(
            role=MessageRole.USER,
            content="Turn on WiFi"
        )
        
        assert msg.role == MessageRole.USER
        assert msg.content == "Turn on WiFi"
        assert msg.timestamp is not None


class TestActionResult:
    """Tests for ActionResult dataclass"""
    
    def test_success_result(self):
        """Test successful ActionResult"""
        action = Action(type=ActionType.CLICK, description="Click button")
        result = ActionResult(
            action=action,
            success=True,
            message="WiFi enabled",
            output={"status": "connected"}
        )
        
        assert result.success
        assert result.message == "WiFi enabled"
        assert result.output["status"] == "connected"
    
    def test_failure_result(self):
        """Test failed ActionResult"""
        action = Action(type=ActionType.CLICK, description="Click button")
        result = ActionResult(
            action=action,
            success=False,
            message="Failed",
            error="Connection timeout",
            suggested_recovery=RecoveryStrategy.RETRY
        )
        
        assert not result.success
        assert result.error == "Connection timeout"
        assert result.suggested_recovery == RecoveryStrategy.RETRY


class TestTaskIntent:
    """Tests for TaskIntent dataclass"""
    
    def test_intent_creation(self):
        """Test TaskIntent creation"""
        intent = TaskIntent(
            type=IntentType.SYSTEM_CONTROL,
            raw_input="turn on wifi",
            confidence=0.95,
            matched_command="wifi_on",
            is_direct_command=True
        )
        
        assert intent.type == IntentType.SYSTEM_CONTROL
        assert intent.raw_input == "turn on wifi"
        assert intent.confidence == 0.95
        assert intent.is_direct_command
    
    def test_complex_intent(self):
        """Test complex multi-step intent"""
        intent = TaskIntent(
            type=IntentType.MULTI_STEP_TASK,
            raw_input="send hello to John on WhatsApp",
            confidence=0.8,
            target_app="WhatsApp",
            subtasks=["open WhatsApp", "find contact", "send message"]
        )
        
        assert intent.type == IntentType.MULTI_STEP_TASK
        assert intent.target_app == "WhatsApp"
        assert len(intent.subtasks) == 3


class TestClarification:
    """Tests for Clarification dataclass"""
    
    def test_clarification_creation(self):
        """Test Clarification creation"""
        clarification = Clarification(
            question="Which contact do you want to message?",
            context="Multiple contacts found",
            options=["John Smith", "John Doe", "John Brown"]
        )
        
        assert clarification.question == "Which contact do you want to message?"
        assert len(clarification.options) == 3
        assert not clarification.answered


class TestSuggestion:
    """Tests for Suggestion dataclass"""
    
    def test_suggestion_creation(self):
        """Test Suggestion creation"""
        suggestion = Suggestion(
            text="Try opening Safari first",
            confidence=Confidence.HIGH,
            alternatives=["Use Chrome instead", "Check internet connection"]
        )
        
        assert suggestion.text == "Try opening Safari first"
        assert suggestion.confidence == Confidence.HIGH
        assert len(suggestion.alternatives) == 2


class TestExecutionContext:
    """Tests for ExecutionContext dataclass"""
    
    def test_context_creation(self):
        """Test ExecutionContext creation"""
        context = ExecutionContext()
        
        assert context.current_task is None
        assert context.current_plan is None
        assert context.current_step_index == 0
        assert len(context.conversation_history) == 0
        assert len(context.element_cache) == 0
    
    def test_context_with_data(self):
        """Test context with populated data"""
        msg = ConversationMessage(role=MessageRole.USER, content="Hello")
        
        context = ExecutionContext(
            current_task="Open Safari",
            current_step_index=2,
            conversation_history=[msg],
            element_cache={"button": (100, 200)}
        )
        
        assert context.current_task == "Open Safari"
        assert context.current_step_index == 2
        assert len(context.conversation_history) == 1
        assert context.element_cache["button"] == (100, 200)
