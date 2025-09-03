import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from utils.logger import setup_logger
from config.settings import DB_FILE

logger = setup_logger(__name__)

class DatabaseManager:
    """Database operations manager"""
    
    def __init__(self):
        self.db_file = DB_FILE
        self.init_database()
    
    def init_database(self):
        """Database-ը և աղյուսակները ստեղծել"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            server_id TEXT NOT NULL,
            original_content TEXT,
            attachment_urls TEXT,
            timestamp DATETIME NOT NULL,
            ai_status TEXT,
            ai_feedback TEXT,
            action_taken TEXT,
            processing_time REAL
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def log_message_event(self, message_id: str, user_id: str, username: str, 
                         channel_id: str, server_id: str, original_content: str,
                         attachment_urls: List[str], ai_status: Optional[str] = None,
                         ai_feedback: Optional[str] = None, action_taken: Optional[str] = None,
                         processing_time: Optional[float] = None):
        """Նամակի մանրամասները database-ում պահել"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO message_logs (
            message_id, user_id, username, channel_id, server_id,
            original_content, attachment_urls, timestamp, ai_status,
            ai_feedback, action_taken, processing_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            message_id, user_id, username, channel_id, server_id,
            original_content, json.dumps(attachment_urls), datetime.now(),
            ai_status, ai_feedback, action_taken, processing_time
        ))
        
        conn.commit()
        conn.close()
    
    def cleanup_old_logs(self, days: int = 30):
        """Հին logs-երը ջնջել"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cursor.execute(
            "DELETE FROM message_logs WHERE timestamp < ?",
            (cutoff_date,)
        )
        
        deleted_rows = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted_rows > 0:
            logger.info(f"Cleaned up {deleted_rows} old log entries")
        
        return deleted_rows
    
    def get_user_stats(self, user_id: str, days: int = 30) -> Dict[str, int]:
        """Օգտատիրոջ վիճակագրությունը ստանալ"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cursor.execute('''
        SELECT ai_status, COUNT(*) 
        FROM message_logs 
        WHERE user_id = ? AND timestamp >= ?
        GROUP BY ai_status
        ''', (user_id, cutoff_date))
        
        results = cursor.fetchall()
        conn.close()
        
        stats = {
            'total': 0,
            'approved': 0,
            'rejected': 0,
            'needs_edit': 0,
            'error': 0
        }
        
        for status, count in results:
            if status == 'approve':
                stats['approved'] = count
            elif status == 'reject':
                stats['rejected'] = count
            elif status == 'needs_edit':
                stats['needs_edit'] = count
            elif status == 'error':
                stats['error'] = count
            
            stats['total'] += count
        
        return stats
    
    def get_recent_logs(self, limit: int = 10) -> List[Tuple]:
        """Վերջին logs-երը ստանալ"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT username, ai_status, timestamp, 
               CASE 
                   WHEN LENGTH(original_content) > 50 
                   THEN SUBSTR(original_content, 1, 50) || '...'
                   ELSE original_content
               END as short_content
        FROM message_logs 
        ORDER BY timestamp DESC 
        LIMIT ?
        ''', (limit,))
        
        logs = cursor.fetchall()
        conn.close()
        
        return logs