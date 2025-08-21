"""
Article Editor - AI-powered document editing using Claude API.
"""

__version__ = "1.0.0"
__author__ = "Article Editor Development Team"
__email__ = "contact@articleeditor.dev"
__license__ = "MIT"

from .core.processor import ArticleProcessor
from .core.chunker import TextChunker
from .core.batch_processor import BatchProcessor, BatchJob
from .api.claude_client import ClaudeClient, AsyncClaudeClient
from .utils.file_handler import FileHandler
from .utils.logger import setup_logging, get_logger, get_session_logger
from .utils.exceptions import (
    ArticleEditorError,
    FileProcessingError,
    UnsupportedFileFormatError,
    APIError,
    RateLimitError,
    AuthenticationError,
    ProcessingError
)

__all__ = [
    "ArticleProcessor",
    "TextChunker", 
    "BatchProcessor",
    "BatchJob",
    "ClaudeClient",
    "AsyncClaudeClient",
    "FileHandler",
    "setup_logging",
    "get_logger",
    "get_session_logger",
    "ArticleEditorError",
    "FileProcessingError",
    "UnsupportedFileFormatError", 
    "APIError",
    "RateLimitError",
    "AuthenticationError",
    "ProcessingError"
]