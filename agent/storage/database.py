"""
Agent Database - SQLite storage for agent data

Provides persistent storage for:
- Task history
- Screenshots with metadata
- User preferences
- Audit logs
"""
import sqlite3
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import contextmanager

from ..core.config import PROJECT_ROOT

logger = logging.getLogger(__name__)


class AgentDatabase:
    """
    SQLite database for agent persistence.
    
    Tables:
    - tasks: Task execution history
    - screenshots: Screenshot metadata
    - preferences: User preferences
    - audit_log: Action audit trail
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database.
        
        Args:
            db_path: Path to database file (default: PROJECT_ROOT/.cache/agent.db)
        """
        if db_path is None:
            db_path = str(PROJECT_ROOT / ".cache" / "agent.db")
        
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._init_schema()
        logger.debug(f"Database initialized at {db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_schema(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    input TEXT NOT NULL,
                    intent_type TEXT,
                    plan_json TEXT,
                    result_json TEXT,
                    success INTEGER,
                    duration_sec REAL,
                    steps_completed INTEGER,
                    steps_total INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            
            # Screenshots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS screenshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filepath TEXT NOT NULL,
                    analysis_json TEXT,
                    active_app TEXT,
                    width INTEGER,
                    height INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Audit log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT NOT NULL,
                    description TEXT,
                    details_json TEXT,
                    success INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_screenshots_created ON screenshots(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at)")
    
    # =========================================================================
    # Task Methods
    # =========================================================================
    
    def save_task(
        self,
        input_text: str,
        intent_type: Optional[str] = None,
        plan: Optional[Dict] = None,
        result: Optional[Dict] = None,
        success: bool = False,
        duration_sec: float = 0.0,
        steps_completed: int = 0,
        steps_total: int = 0
    ) -> int:
        """
        Save a task execution record.
        
        Returns:
            Task ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks 
                (input, intent_type, plan_json, result_json, success, 
                 duration_sec, steps_completed, steps_total, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                input_text,
                intent_type,
                json.dumps(plan) if plan else None,
                json.dumps(result) if result else None,
                1 if success else 0,
                duration_sec,
                steps_completed,
                steps_total,
                datetime.now().isoformat()
            ))
            return cursor.lastrowid
    
    def get_recent_tasks(self, limit: int = 10) -> List[Dict]:
        """Get recent task history"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tasks 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_task_stats(self) -> Dict[str, Any]:
        """Get task execution statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM tasks")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE success = 1")
            successful = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(duration_sec) FROM tasks WHERE success = 1")
            avg_duration = cursor.fetchone()[0] or 0
            
            return {
                "total_tasks": total,
                "successful_tasks": successful,
                "success_rate": successful / total if total > 0 else 0,
                "avg_duration_sec": round(avg_duration, 2)
            }
    
    # =========================================================================
    # Screenshot Methods
    # =========================================================================
    
    def save_screenshot(
        self,
        filepath: str,
        analysis: Optional[Dict] = None,
        active_app: Optional[str] = None,
        width: int = 0,
        height: int = 0
    ) -> int:
        """
        Save screenshot metadata.
        
        Returns:
            Screenshot ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO screenshots 
                (filepath, analysis_json, active_app, width, height)
                VALUES (?, ?, ?, ?, ?)
            """, (
                filepath,
                json.dumps(analysis) if analysis else None,
                active_app,
                width,
                height
            ))
            return cursor.lastrowid
    
    def get_recent_screenshots(self, limit: int = 10) -> List[Dict]:
        """Get recent screenshots"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM screenshots 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def delete_old_screenshots(self, days: int = 7) -> int:
        """
        Delete screenshot records older than specified days.
        
        Returns:
            Number of deleted records
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM screenshots 
                WHERE created_at < datetime('now', ?)
            """, (f'-{days} days',))
            return cursor.rowcount
    
    # =========================================================================
    # Preferences Methods
    # =========================================================================
    
    def set_preference(self, key: str, value: Any) -> None:
        """Set a preference value"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO preferences (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, json.dumps(value), datetime.now().isoformat()))
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a preference value"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
            row = cursor.fetchone()
            
            if row:
                return json.loads(row['value'])
            return default
    
    def get_all_preferences(self) -> Dict[str, Any]:
        """Get all preferences"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM preferences")
            
            prefs = {}
            for row in cursor.fetchall():
                prefs[row['key']] = json.loads(row['value'])
            return prefs
    
    # =========================================================================
    # Audit Log Methods
    # =========================================================================
    
    def log_action(
        self,
        action_type: str,
        description: str,
        details: Optional[Dict] = None,
        success: bool = True
    ) -> int:
        """
        Log an action for audit trail.
        
        Returns:
            Log entry ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_log (action_type, description, details_json, success)
                VALUES (?, ?, ?, ?)
            """, (
                action_type,
                description,
                json.dumps(details) if details else None,
                1 if success else 0
            ))
            return cursor.lastrowid
    
    def get_audit_log(self, limit: int = 50) -> List[Dict]:
        """Get recent audit log entries"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM audit_log 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def clear_old_logs(self, days: int = 30) -> int:
        """
        Clear audit logs older than specified days.
        
        Returns:
            Number of deleted entries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM audit_log 
                WHERE created_at < datetime('now', ?)
            """, (f'-{days} days',))
            return cursor.rowcount


# Global database instance
agent_db = AgentDatabase()
