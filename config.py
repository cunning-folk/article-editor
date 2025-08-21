"""
Configuration management for Article Editor.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging


@dataclass
class ModelConfig:
    """Configuration for AI models."""
    name: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 100000
    temperature: float = 0.1
    timeout: int = 300  # seconds


@dataclass
class ChunkingConfig:
    """Configuration for text chunking."""
    default_chunk_size: int = 15000
    default_overlap: int = 500
    min_chunk_size: int = 1000
    max_chunk_size: int = 100000
    max_overlap_ratio: float = 0.3  # overlap can't be more than 30% of chunk size


@dataclass
class RateLimitConfig:
    """Configuration for API rate limiting."""
    requests_per_minute: int = 50
    tokens_per_minute: int = 100000
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0


@dataclass
class WebConfig:
    """Configuration for web interface."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    upload_dir: str = "uploads"
    output_dir: str = "outputs"
    session_timeout: int = 3600  # 1 hour


@dataclass
class LoggingConfig:
    """Configuration for logging."""
    level: str = "INFO"
    log_dir: str = "logs"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    session_log_retention_days: int = 7


@dataclass
class SecurityConfig:
    """Configuration for security settings."""
    allowed_origins: list = None
    max_concurrent_sessions: int = 100
    api_key_validation: bool = True
    file_type_validation: bool = True
    
    def __post_init__(self):
        if self.allowed_origins is None:
            self.allowed_origins = ["*"]


@dataclass
class AppConfig:
    """Main application configuration."""
    model: ModelConfig = None
    chunking: ChunkingConfig = None
    rate_limit: RateLimitConfig = None
    web: WebConfig = None
    logging: LoggingConfig = None
    security: SecurityConfig = None
    
    def __post_init__(self):
        if self.model is None:
            self.model = ModelConfig()
        if self.chunking is None:
            self.chunking = ChunkingConfig()
        if self.rate_limit is None:
            self.rate_limit = RateLimitConfig()
        if self.web is None:
            self.web = WebConfig()
        if self.logging is None:
            self.logging = LoggingConfig()
        if self.security is None:
            self.security = SecurityConfig()


class ConfigManager:
    """Manages application configuration from multiple sources."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "config.json"
        self.config = AppConfig()
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file and environment variables."""
        # Load from file first
        self._load_from_file()
        
        # Override with environment variables
        self._load_from_env()
        
        # Validate configuration
        self._validate_config()
    
    def _load_from_file(self):
        """Load configuration from JSON file."""
        config_path = Path(self.config_file)
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                
                # Update configuration with file data
                self._update_config_from_dict(config_data)
                self.logger.info(f"Configuration loaded from {config_path}")
                
            except Exception as e:
                self.logger.warning(f"Failed to load config file {config_path}: {e}")
        else:
            self.logger.info(f"Config file {config_path} not found, using defaults")
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        env_mappings = {
            # Model config
            "ARTICLE_EDITOR_MODEL": ("model", "name"),
            "ARTICLE_EDITOR_MAX_TOKENS": ("model", "max_tokens", int),
            "ARTICLE_EDITOR_TEMPERATURE": ("model", "temperature", float),
            
            # Chunking config
            "ARTICLE_EDITOR_CHUNK_SIZE": ("chunking", "default_chunk_size", int),
            "ARTICLE_EDITOR_OVERLAP": ("chunking", "default_overlap", int),
            
            # Rate limit config
            "ARTICLE_EDITOR_RATE_LIMIT_RPM": ("rate_limit", "requests_per_minute", int),
            "ARTICLE_EDITOR_RATE_LIMIT_TPM": ("rate_limit", "tokens_per_minute", int),
            
            # Web config
            "ARTICLE_EDITOR_HOST": ("web", "host"),
            "ARTICLE_EDITOR_PORT": ("web", "port", int),
            "ARTICLE_EDITOR_DEBUG": ("web", "debug", bool),
            "ARTICLE_EDITOR_MAX_FILE_SIZE": ("web", "max_file_size", int),
            
            # Logging config
            "ARTICLE_EDITOR_LOG_LEVEL": ("logging", "level"),
            "ARTICLE_EDITOR_LOG_DIR": ("logging", "log_dir"),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                try:
                    # Parse value type if specified
                    if len(config_path) > 2:
                        value_type = config_path[2]
                        if value_type == int:
                            value = int(value)
                        elif value_type == float:
                            value = float(value)
                        elif value_type == bool:
                            value = value.lower() in ('true', '1', 'yes', 'on')
                    
                    # Set configuration value
                    config_obj = getattr(self.config, config_path[0])
                    setattr(config_obj, config_path[1], value)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to parse environment variable {env_var}={value}: {e}")
    
    def _update_config_from_dict(self, config_data: Dict[str, Any]):
        """Update configuration from dictionary."""
        for section, values in config_data.items():
            if hasattr(self.config, section) and isinstance(values, dict):
                config_obj = getattr(self.config, section)
                for key, value in values.items():
                    if hasattr(config_obj, key):
                        setattr(config_obj, key, value)
    
    def _validate_config(self):
        """Validate configuration values."""
        # Validate chunking config
        if self.config.chunking.default_chunk_size < self.config.chunking.min_chunk_size:
            self.config.chunking.default_chunk_size = self.config.chunking.min_chunk_size
            self.logger.warning(f"Adjusted chunk size to minimum: {self.config.chunking.min_chunk_size}")
        
        if self.config.chunking.default_chunk_size > self.config.chunking.max_chunk_size:
            self.config.chunking.default_chunk_size = self.config.chunking.max_chunk_size
            self.logger.warning(f"Adjusted chunk size to maximum: {self.config.chunking.max_chunk_size}")
        
        max_overlap = int(self.config.chunking.default_chunk_size * self.config.chunking.max_overlap_ratio)
        if self.config.chunking.default_overlap > max_overlap:
            self.config.chunking.default_overlap = max_overlap
            self.logger.warning(f"Adjusted overlap to maximum allowed: {max_overlap}")
        
        # Validate web config
        if self.config.web.port < 1 or self.config.web.port > 65535:
            self.config.web.port = 8000
            self.logger.warning("Invalid port, using default: 8000")
        
        # Create directories
        Path(self.config.web.upload_dir).mkdir(exist_ok=True)
        Path(self.config.web.output_dir).mkdir(exist_ok=True)
        Path(self.config.logging.log_dir).mkdir(exist_ok=True)
    
    def save_config(self, file_path: Optional[str] = None):
        """Save current configuration to file."""
        save_path = file_path or self.config_file
        
        try:
            config_dict = asdict(self.config)
            with open(save_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            self.logger.info(f"Configuration saved to {save_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
    
    def get_config(self) -> AppConfig:
        """Get the current configuration."""
        return self.config
    
    def update_config(self, **kwargs):
        """Update configuration values."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        self._validate_config()


# Global configuration instance
_config_manager = None


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.get_config()


def init_config(config_file: Optional[str] = None) -> ConfigManager:
    """Initialize the global configuration manager."""
    global _config_manager
    _config_manager = ConfigManager(config_file)
    return _config_manager


def save_config(file_path: Optional[str] = None):
    """Save the global configuration to file."""
    global _config_manager
    if _config_manager:
        _config_manager.save_config(file_path)