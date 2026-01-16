"""
Commands Package - Direct command system for instant execution
"""
from .command_registry import (
    CommandRegistry,
    DirectCommand,
    SystemCommand,
    AppCommand,
    command_registry
)
from .command_matcher import CommandMatcher, command_matcher

__all__ = [
    'CommandRegistry',
    'DirectCommand',
    'SystemCommand', 
    'AppCommand',
    'CommandMatcher',
    'command_registry',
    'command_matcher'
]

