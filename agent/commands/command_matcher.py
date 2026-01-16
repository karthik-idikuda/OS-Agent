"""
Command Matcher - Fuzzy matching for natural language commands

This module provides sophisticated matching between user input and registered
commands, handling variations, typos, and parameter extraction.
"""
import re
import logging
from difflib import SequenceMatcher
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of command matching"""
    matched: bool
    command_name: Optional[str] = None
    confidence: float = 0.0
    params: Dict[str, Any] = None
    matched_alias: Optional[str] = None
    
    def __post_init__(self):
        if self.params is None:
            self.params = {}


class CommandMatcher:
    """
    Fuzzy matcher for natural language commands.
    
    Handles:
    - Exact matches
    - Prefix matches
    - Similarity-based fuzzy matching
    - Parameter extraction
    - Synonym expansion
    """
    
    # Synonyms for common words
    SYNONYMS = {
        "turn on": ["enable", "activate", "start", "switch on"],
        "turn off": ["disable", "deactivate", "stop", "switch off"],
        "open": ["launch", "start", "run"],
        "close": ["quit", "exit", "terminate", "kill"],
        "increase": ["raise", "turn up", "higher", "more"],
        "decrease": ["lower", "turn down", "reduce", "less"],
        "go to": ["navigate to", "visit", "open", "browse to"],
        "enable": ["turn on", "activate", "switch on"],
        "disable": ["turn off", "deactivate", "switch off"],
    }
    
    # Words to ignore for matching
    STOP_WORDS = {"the", "a", "an", "please", "can", "you", "could", "would", "my", "me"}
    
    def __init__(self, similarity_threshold: float = 0.7):
        """
        Initialize matcher.
        
        Args:
            similarity_threshold: Minimum similarity score for fuzzy matching (0-1)
        """
        self.similarity_threshold = similarity_threshold
    
    def normalize(self, text: str) -> str:
        """
        Normalize text for matching.
        
        - Lowercase
        - Remove punctuation
        - Remove stop words
        - Collapse whitespace
        """
        text = text.lower().strip()
        # Remove punctuation except for URLs
        if not re.search(r'https?://', text):
            text = re.sub(r'[^\w\s]', '', text)
        # Remove stop words
        words = text.split()
        words = [w for w in words if w not in self.STOP_WORDS]
        return ' '.join(words)
    
    def expand_synonyms(self, text: str) -> List[str]:
        """
        Expand text to include synonym variations.
        
        Returns list of possible interpretations.
        """
        variations = [text]
        
        for phrase, synonyms in self.SYNONYMS.items():
            if phrase in text:
                for syn in synonyms:
                    variations.append(text.replace(phrase, syn))
            for syn in synonyms:
                if syn in text:
                    variations.append(text.replace(syn, phrase))
        
        return list(set(variations))
    
    def similarity(self, a: str, b: str) -> float:
        """Calculate similarity between two strings (0-1)"""
        return SequenceMatcher(None, a, b).ratio()
    
    def word_overlap(self, a: str, b: str) -> float:
        """Calculate word overlap between two strings (0-1)"""
        words_a = set(a.split())
        words_b = set(b.split())
        if not words_a or not words_b:
            return 0.0
        
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)
    
    def find_best_match(
        self,
        user_input: str,
        aliases: Dict[str, str]
    ) -> MatchResult:
        """
        Find the best matching command for user input.
        
        Args:
            user_input: Natural language input from user
            aliases: Dict mapping alias strings to command names
        
        Returns:
            MatchResult with best match and confidence
        """
        normalized_input = self.normalize(user_input)
        variations = self.expand_synonyms(normalized_input)
        
        best_match = MatchResult(matched=False)
        
        for variation in variations:
            for alias, cmd_name in aliases.items():
                normalized_alias = self.normalize(alias)
                
                # Exact match
                if variation == normalized_alias:
                    return MatchResult(
                        matched=True,
                        command_name=cmd_name,
                        confidence=1.0,
                        matched_alias=alias
                    )
                
                # Prefix match
                if variation.startswith(normalized_alias):
                    confidence = len(normalized_alias) / len(variation) * 0.95
                    if confidence > best_match.confidence:
                        remaining = variation[len(normalized_alias):].strip()
                        best_match = MatchResult(
                            matched=True,
                            command_name=cmd_name,
                            confidence=confidence,
                            matched_alias=alias,
                            params={"_remaining": remaining} if remaining else {}
                        )
                
                # Contains match (alias within input)
                if normalized_alias in variation:
                    confidence = len(normalized_alias) / len(variation) * 0.9
                    if confidence > best_match.confidence:
                        best_match = MatchResult(
                            matched=True,
                            command_name=cmd_name,
                            confidence=confidence,
                            matched_alias=alias
                        )
                
                # Fuzzy match using string similarity
                sim = self.similarity(variation, normalized_alias)
                if sim >= self.similarity_threshold and sim > best_match.confidence:
                    best_match = MatchResult(
                        matched=True,
                        command_name=cmd_name,
                        confidence=sim,
                        matched_alias=alias
                    )
                
                # Word overlap match
                overlap = self.word_overlap(variation, normalized_alias)
                if overlap >= self.similarity_threshold and overlap > best_match.confidence:
                    best_match = MatchResult(
                        matched=True,
                        command_name=cmd_name,
                        confidence=overlap * 0.9,  # Slightly lower weight
                        matched_alias=alias
                    )
        
        return best_match
    
    def extract_number(self, text: str) -> Optional[int]:
        """Extract a number from text"""
        # Handle "fifty" -> 50 etc.
        word_numbers = {
            "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
            "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
            "ten": 10, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
            "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
            "hundred": 100, "max": 100, "maximum": 100, "full": 100,
            "half": 50, "quarter": 25
        }
        
        text_lower = text.lower()
        
        # Check for word numbers
        for word, value in word_numbers.items():
            if word in text_lower:
                return value
        
        # Check for digit numbers
        match = re.search(r'(\d+)', text)
        if match:
            return int(match.group(1))
        
        return None
    
    def extract_app_name(self, text: str) -> Optional[str]:
        """Extract application name from text"""
        # Common app names
        apps = [
            "safari", "chrome", "firefox", "finder", "terminal",
            "notes", "calendar", "mail", "messages", "whatsapp",
            "telegram", "slack", "discord", "spotify", "music",
            "photos", "settings", "calculator", "preview", "vscode"
        ]
        
        text_lower = text.lower()
        for app in apps:
            if app in text_lower:
                return app
        
        return None
    
    def extract_url(self, text: str) -> Optional[str]:
        """Extract URL from text"""
        # Match URLs
        url_pattern = r'https?://[^\s]+'
        match = re.search(url_pattern, text)
        if match:
            return match.group(0)
        
        # Match domain-like strings
        domain_pattern = r'([a-zA-Z0-9-]+\.[a-zA-Z]{2,})'
        match = re.search(domain_pattern, text)
        if match:
            return match.group(1)
        
        return None
    
    def extract_params(
        self,
        user_input: str,
        command_name: str,
        param_name: Optional[str]
    ) -> Dict[str, Any]:
        """
        Extract parameters from user input based on command type.
        
        Args:
            user_input: The original user input
            command_name: Name of the matched command
            param_name: Expected parameter name if any
        
        Returns:
            Dict of extracted parameters
        """
        params = {}
        
        if param_name == "level":
            level = self.extract_number(user_input)
            if level is not None:
                params["level"] = min(100, max(0, level))
        
        elif param_name == "url":
            url = self.extract_url(user_input)
            if url:
                params["url"] = url
        
        elif param_name == "app":
            app = self.extract_app_name(user_input)
            if app:
                params["app"] = app
        
        return params
    
    def get_suggestions(
        self,
        user_input: str,
        aliases: Dict[str, str],
        max_suggestions: int = 3
    ) -> List[Tuple[str, float]]:
        """
        Get command suggestions when no direct match found.
        
        Args:
            user_input: User's input
            aliases: Dict of aliases to command names
            max_suggestions: Maximum suggestions to return
        
        Returns:
            List of (command_name, confidence) tuples
        """
        normalized = self.normalize(user_input)
        suggestions = []
        
        for alias, cmd_name in aliases.items():
            normalized_alias = self.normalize(alias)
            
            # Calculate combined score
            sim_score = self.similarity(normalized, normalized_alias)
            overlap_score = self.word_overlap(normalized, normalized_alias)
            combined_score = (sim_score + overlap_score) / 2
            
            if combined_score > 0.3:  # Minimum threshold for suggestions
                suggestions.append((cmd_name, alias, combined_score))
        
        # Sort by score and deduplicate command names
        suggestions.sort(key=lambda x: x[2], reverse=True)
        
        seen_commands = set()
        unique_suggestions = []
        for cmd_name, alias, score in suggestions:
            if cmd_name not in seen_commands:
                seen_commands.add(cmd_name)
                unique_suggestions.append((cmd_name, score))
                if len(unique_suggestions) >= max_suggestions:
                    break
        
        return unique_suggestions


# Global matcher instance
command_matcher = CommandMatcher()
