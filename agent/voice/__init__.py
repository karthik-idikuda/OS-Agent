"""
Voice module initialization
"""
from .interface import VoiceInterface, VoiceConfig, SimpleVoiceInput
from .enhanced_interface import (
    EnhancedVoiceInterface,
    EnhancedVoiceConfig,
    TTSVoice,
    VoiceFeedback,
    create_voice_interface
)

__all__ = [
    # Original
    "VoiceInterface",
    "VoiceConfig",
    "SimpleVoiceInput",
    # Enhanced
    "EnhancedVoiceInterface",
    "EnhancedVoiceConfig",
    "TTSVoice",
    "VoiceFeedback",
    "create_voice_interface",
]

