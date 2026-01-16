"""
Logging utilities
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None
) -> logging.Logger:
    """
    Setup logging for the agent.
    
    Args:
        level: Logging level
        log_file: Optional log file name
        log_dir: Optional log directory
    
    Returns:
        Root logger
    """
    # Create log directory
    if log_dir:
        log_path = Path(log_dir)
    else:
        log_path = Path("logs")
    
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Generate log file name
    if not log_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"agent_{timestamp}.log"
    
    log_file_path = log_path / log_file
    
    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    console_formatter = logging.Formatter(
        "%(levelname)-8s | %(message)s"
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Set levels for noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    
    return root_logger


class ActionLogger:
    """Logger for agent actions with structured output"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Action log file
        self.action_log = self.log_dir / "actions.jsonl"
        self.logger = logging.getLogger("actions")
    
    def log_action(
        self,
        action_type: str,
        description: str,
        params: dict = None,
        result: dict = None
    ):
        """Log an action"""
        import json
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action_type,
            "description": description,
            "params": params or {},
            "result": result or {}
        }
        
        # Append to JSONL file
        with open(self.action_log, "a") as f:
            f.write(json.dumps(entry) + "\n")
        
        # Also log to standard logger
        status = "✓" if result and result.get("success") else "✗"
        self.logger.info(f"{status} {action_type}: {description}")
    
    def log_task_start(self, task: str):
        """Log task start"""
        self.log_action("TASK_START", task)
    
    def log_task_end(self, task: str, success: bool):
        """Log task end"""
        self.log_action("TASK_END", task, result={"success": success})
    
    def get_recent_actions(self, limit: int = 10) -> list:
        """Get recent actions from log"""
        import json
        
        if not self.action_log.exists():
            return []
        
        actions = []
        with open(self.action_log, "r") as f:
            for line in f:
                try:
                    actions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        
        return actions[-limit:]
