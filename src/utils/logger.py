"""
Centralized logging configuration for the Article Editor.
"""

import logging
import logging.handlers
import sys
import os
from pathlib import Path
from typing import Optional
from datetime import datetime


class ArticleEditorLogger:
    """Centralized logger configuration for the Article Editor application."""
    
    def __init__(self, log_dir: Optional[str] = None, log_level: str = "INFO"):
        self.log_dir = Path(log_dir) if log_dir else Path("logs")
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging with both file and console handlers."""
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handler for all logs
        all_logs_file = self.log_dir / "article_editor.log"
        file_handler = logging.handlers.RotatingFileHandler(
            all_logs_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
        
        # Error-specific file handler
        error_logs_file = self.log_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_logs_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)
        
        # Session-specific handler (for web sessions)
        self._setup_session_logger()
        
        # Set levels for external libraries
        logging.getLogger("anthropic").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("uvicorn").setLevel(logging.INFO)
        logging.getLogger("fastapi").setLevel(logging.INFO)
    
    def _setup_session_logger(self):
        """Setup logger for session-specific logs."""
        session_logger = logging.getLogger("session")
        session_logger.setLevel(logging.INFO)
        
        # Session log handler
        session_logs_file = self.log_dir / "sessions.log"
        session_handler = logging.handlers.RotatingFileHandler(
            session_logs_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3
        )
        session_handler.setLevel(logging.INFO)
        
        session_formatter = logging.Formatter(
            '%(asctime)s - SESSION - %(message)s'
        )
        session_handler.setFormatter(session_formatter)
        session_logger.addHandler(session_handler)
        
        # Prevent propagation to avoid duplicate logs
        session_logger.propagate = False
    
    def get_session_logger(self, session_id: str) -> logging.Logger:
        """Get a logger for a specific session."""
        logger_name = f"session.{session_id}"
        logger = logging.getLogger(logger_name)
        
        if not logger.handlers:
            # Create session-specific file handler
            session_file = self.log_dir / f"session_{session_id}.log"
            handler = logging.FileHandler(session_file)
            handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            logger.propagate = True  # Also log to main loggers
        
        return logger
    
    def cleanup_old_session_logs(self, days_to_keep: int = 7):
        """Clean up old session log files."""
        cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
        
        for log_file in self.log_dir.glob("session_*.log"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    logging.info(f"Cleaned up old session log: {log_file}")
                except Exception as e:
                    logging.warning(f"Failed to clean up log file {log_file}: {e}")


class PerformanceLogger:
    """Logger for performance metrics and timing."""
    
    def __init__(self):
        self.logger = logging.getLogger("performance")
        self.start_times = {}
    
    def start_timer(self, operation_name: str, **context):
        """Start timing an operation."""
        self.start_times[operation_name] = datetime.now()
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        self.logger.info(f"STARTED: {operation_name} - {context_str}")
    
    def end_timer(self, operation_name: str, **context):
        """End timing an operation and log the duration."""
        if operation_name in self.start_times:
            duration = (datetime.now() - self.start_times[operation_name]).total_seconds()
            del self.start_times[operation_name]
            
            context_str = ", ".join(f"{k}={v}" for k, v in context.items())
            self.logger.info(f"COMPLETED: {operation_name} - Duration: {duration:.2f}s - {context_str}")
            return duration
        else:
            self.logger.warning(f"Timer not found for operation: {operation_name}")
            return None
    
    def log_metric(self, metric_name: str, value: float, unit: str = "", **context):
        """Log a performance metric."""
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        self.logger.info(f"METRIC: {metric_name} = {value}{unit} - {context_str}")


class AuditLogger:
    """Logger for audit trail and user actions."""
    
    def __init__(self):
        self.logger = logging.getLogger("audit")
    
    def log_file_upload(self, filename: str, file_size: int, user_ip: str = None):
        """Log file upload event."""
        self.logger.info(f"FILE_UPLOAD: {filename} ({file_size} bytes) from {user_ip or 'unknown'}")
    
    def log_processing_start(self, session_id: str, filename: str, model: str, **options):
        """Log processing start event."""
        options_str = ", ".join(f"{k}={v}" for k, v in options.items())
        self.logger.info(f"PROCESSING_START: session={session_id}, file={filename}, model={model}, options=({options_str})")
    
    def log_processing_end(self, session_id: str, success: bool, duration: float, **metrics):
        """Log processing completion event."""
        status = "SUCCESS" if success else "FAILED"
        metrics_str = ", ".join(f"{k}={v}" for k, v in metrics.items())
        self.logger.info(f"PROCESSING_END: session={session_id}, status={status}, duration={duration:.2f}s, metrics=({metrics_str})")
    
    def log_download(self, session_id: str, filename: str, user_ip: str = None):
        """Log file download event."""
        self.logger.info(f"DOWNLOAD: session={session_id}, file={filename} by {user_ip or 'unknown'}")
    
    def log_api_call(self, model: str, input_tokens: int, output_tokens: int, cost: float):
        """Log API call metrics."""
        self.logger.info(f"API_CALL: model={model}, input_tokens={input_tokens}, output_tokens={output_tokens}, cost=${cost:.6f}")


# Global logger instances
_main_logger = None
_performance_logger = None
_audit_logger = None


def setup_logging(log_dir: Optional[str] = None, log_level: str = "INFO"):
    """Setup global logging configuration."""
    global _main_logger, _performance_logger, _audit_logger
    
    _main_logger = ArticleEditorLogger(log_dir, log_level)
    _performance_logger = PerformanceLogger()
    _audit_logger = AuditLogger()
    
    logging.info("Article Editor logging system initialized")


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name) if name else logging.getLogger()


def get_session_logger(session_id: str) -> logging.Logger:
    """Get a session-specific logger."""
    if _main_logger:
        return _main_logger.get_session_logger(session_id)
    return logging.getLogger(f"session.{session_id}")


def get_performance_logger() -> PerformanceLogger:
    """Get the performance logger."""
    return _performance_logger or PerformanceLogger()


def get_audit_logger() -> AuditLogger:
    """Get the audit logger."""
    return _audit_logger or AuditLogger()


def cleanup_logs(days_to_keep: int = 7):
    """Clean up old log files."""
    if _main_logger:
        _main_logger.cleanup_old_session_logs(days_to_keep)