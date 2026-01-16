"""
Unit Tests for Command Registry and Matcher
"""
import pytest
from agent.commands.command_registry import (
    CommandRegistry, CommandCategory, CommandResult,
    DirectCommand, SystemCommand, AppCommand, command_registry
)
from agent.commands.command_matcher import CommandMatcher, MatchResult


class TestCommandRegistry:
    """Tests for CommandRegistry class"""
    
    def test_default_commands_registered(self):
        """Test that default commands are registered"""
        registry = CommandRegistry()
        
        assert len(registry.commands) > 0
        assert len(registry.aliases) > 0
        
        # Check specific commands exist
        assert "wifi_on" in registry.commands
        assert "mute" in registry.commands
        assert "screenshot" in registry.commands
    
    def test_wifi_commands(self):
        """Test WiFi commands"""
        registry = CommandRegistry()
        
        # Match variations
        match = registry.match("turn on wifi")
        assert match is not None
        assert match[0].name == "wifi_on"
        
        match = registry.match("enable wifi")
        assert match is not None
        assert match[0].name == "wifi_on"
        
        match = registry.match("wifi off")
        assert match is not None
        assert match[0].name == "wifi_off"
    
    def test_app_commands(self):
        """Test app open/close commands"""
        registry = CommandRegistry()
        
        # Open Safari
        match = registry.match("open safari")
        assert match is not None
        assert "safari" in match[0].name.lower()
        
        # Close Chrome
        match = registry.match("close chrome")
        assert match is not None
        assert "chrome" in match[0].name.lower()
    
    def test_volume_commands(self):
        """Test volume commands"""
        registry = CommandRegistry()
        
        match = registry.match("mute")
        assert match is not None
        assert match[0].name == "mute"
        
        match = registry.match("volume up")
        assert match is not None
        assert match[0].name == "volume_up"
    
    def test_navigation_commands(self):
        """Test URL navigation commands"""
        registry = CommandRegistry()
        
        match = registry.match("go to google")
        assert match is not None
        assert "google" in match[0].name.lower()
        
        match = registry.match("open youtube")
        assert match is not None
    
    def test_no_match(self):
        """Test that non-matching input returns None"""
        registry = CommandRegistry()
        
        match = registry.match("random gibberish text")
        assert match is None
    
    def test_register_custom_command(self):
        """Test registering custom commands"""
        registry = CommandRegistry()
        
        custom = SystemCommand(
            "test_cmd",
            "echo test",
            "Test command",
            success_message="Test executed"
        )
        
        registry.register("test_cmd", custom, aliases=["run test", "do test"])
        
        match = registry.match("run test")
        assert match is not None
        assert match[0].name == "test_cmd"
    
    def test_get_aliases(self):
        """Test getting aliases for a command"""
        registry = CommandRegistry()
        
        aliases = registry.get_aliases("wifi_on")
        assert len(aliases) > 0
        assert "turn on wifi" in aliases
    
    def test_list_commands(self):
        """Test listing commands"""
        registry = CommandRegistry()
        
        all_commands = registry.list_commands()
        assert len(all_commands) > 0
        
        system_commands = registry.list_commands(CommandCategory.SYSTEM)
        assert len(system_commands) > 0
        assert len(system_commands) < len(all_commands)


class TestCommandMatcher:
    """Tests for CommandMatcher class"""
    
    def setup_method(self):
        self.matcher = CommandMatcher()
    
    def test_normalize_basic(self):
        """Test text normalization removes punctuation"""
        # The normalize function keeps common words, just removes punctuation
        result = self.matcher.normalize("Hello World!")
        assert "hello" in result
        assert "world" in result
    
    def test_synonym_expansion(self):
        """Test synonym expansion"""
        variations = self.matcher.expand_synonyms("turn on wifi")
        
        assert "turn on wifi" in variations
        # Check that at least one synonym variant exists
        assert len(variations) >= 1
    
    def test_similarity(self):
        """Test string similarity"""
        # Exact match
        assert self.matcher.similarity("hello", "hello") == 1.0
        
        # Similar strings
        sim = self.matcher.similarity("wifi on", "wifi off")
        assert 0.5 < sim < 1.0
        
        # Different strings
        sim = self.matcher.similarity("hello", "world")
        assert sim < 0.5
    
    def test_word_overlap(self):
        """Test word overlap"""
        # Complete overlap
        assert self.matcher.word_overlap("turn on wifi", "turn on wifi") == 1.0
        
        # Partial overlap
        overlap = self.matcher.word_overlap("turn on wifi", "enable wifi")
        assert 0 < overlap < 1.0
        
        # No overlap
        assert self.matcher.word_overlap("hello", "world") == 0.0
    
    def test_extract_number(self):
        """Test number extraction"""
        assert self.matcher.extract_number("set volume to 50") == 50
        assert self.matcher.extract_number("volume at 75%") == 75
        assert self.matcher.extract_number("half volume") == 50
        assert self.matcher.extract_number("max volume") == 100
        assert self.matcher.extract_number("no numbers here") is None
    
    def test_extract_app_name(self):
        """Test app name extraction"""
        assert self.matcher.extract_app_name("open safari please") == "safari"
        assert self.matcher.extract_app_name("launch chrome browser") == "chrome"
        assert self.matcher.extract_app_name("random text") is None
    
    def test_extract_url(self):
        """Test URL extraction"""
        assert self.matcher.extract_url("go to https://google.com") == "https://google.com"
        assert self.matcher.extract_url("open google.com") == "google.com"
        assert self.matcher.extract_url("no url here") is None
    
    def test_find_best_match_exact(self):
        """Test finding exact match"""
        aliases = {
            "turn on wifi": "wifi_on",
            "enable wifi": "wifi_on",
            "mute": "mute"
        }
        
        result = self.matcher.find_best_match("turn on wifi", aliases)
        assert result.matched
        assert result.command_name == "wifi_on"
        assert result.confidence == 1.0
    
    def test_get_suggestions(self):
        """Test getting suggestions"""
        aliases = {
            "turn on wifi": "wifi_on",
            "turn off wifi": "wifi_off",
            "open safari": "open_safari"
        }
        
        suggestions = self.matcher.get_suggestions("wifi", aliases, max_suggestions=3)
        assert len(suggestions) > 0
        # WiFi related commands should be suggested
        assert any("wifi" in cmd for cmd, _ in suggestions)


class TestCommandResult:
    """Tests for CommandResult dataclass"""
    
    def test_success_result(self):
        """Test successful result"""
        result = CommandResult(
            success=True,
            message="WiFi enabled",
            output="Connected"
        )
        
        assert result.success
        assert result.message == "WiFi enabled"
        assert result.output == "Connected"
        assert result.error is None
    
    def test_failure_result(self):
        """Test failure result"""
        result = CommandResult(
            success=False,
            message="Failed to enable WiFi",
            error="Network error"
        )
        
        assert not result.success
        assert result.error == "Network error"


class TestDirectCommand:
    """Tests for DirectCommand subclasses"""
    
    def test_system_command_properties(self):
        """Test SystemCommand properties"""
        cmd = SystemCommand(
            name="test",
            shell_command="echo test",
            description="Test command",
            success_message="Test done"
        )
        
        assert cmd.name == "test"
        assert cmd.category == CommandCategory.SYSTEM
        assert cmd.description == "Test command"
        assert cmd.success_message == "Test done"
    
    def test_app_command_properties(self):
        """Test AppCommand properties"""
        cmd = AppCommand(
            name="open_test",
            app_name="TestApp",
            action="open",
            description="Open TestApp"
        )
        
        assert cmd.name == "open_test"
        assert cmd.app_name == "TestApp"
        assert cmd.action == "open"
        assert cmd.category == CommandCategory.APP
