"""
Custom exceptions for the Article Editor application.
"""


class ArticleEditorError(Exception):
    """Base exception for Article Editor application."""
    pass


class FileProcessingError(ArticleEditorError):
    """Exception raised when file processing fails."""
    
    def __init__(self, message: str, file_path: str = None, original_error: Exception = None):
        self.file_path = file_path
        self.original_error = original_error
        super().__init__(message)


class UnsupportedFileFormatError(FileProcessingError):
    """Exception raised when file format is not supported."""
    pass


class FileValidationError(FileProcessingError):
    """Exception raised when file validation fails."""
    pass


class ChunkingError(ArticleEditorError):
    """Exception raised when text chunking fails."""
    
    def __init__(self, message: str, chunk_index: int = None, original_error: Exception = None):
        self.chunk_index = chunk_index
        self.original_error = original_error
        super().__init__(message)


class APIError(ArticleEditorError):
    """Exception raised when Claude API calls fail."""
    
    def __init__(self, message: str, error_type: str = None, retry_after: int = None, original_error: Exception = None):
        self.error_type = error_type
        self.retry_after = retry_after
        self.original_error = original_error
        super().__init__(message)


class RateLimitError(APIError):
    """Exception raised when API rate limits are exceeded."""
    
    def __init__(self, message: str, retry_after: int = None, original_error: Exception = None):
        super().__init__(message, "rate_limit", retry_after, original_error)


class AuthenticationError(APIError):
    """Exception raised when API authentication fails."""
    
    def __init__(self, message: str = "Invalid API key or authentication failed", original_error: Exception = None):
        super().__init__(message, "authentication", None, original_error)


class ModelNotAvailableError(APIError):
    """Exception raised when requested model is not available."""
    
    def __init__(self, model: str, original_error: Exception = None):
        message = f"Model '{model}' is not available or accessible"
        super().__init__(message, "model_unavailable", None, original_error)


class TokenLimitError(APIError):
    """Exception raised when token limits are exceeded."""
    
    def __init__(self, message: str, token_count: int = None, original_error: Exception = None):
        self.token_count = token_count
        super().__init__(message, "token_limit", None, original_error)


class ProcessingError(ArticleEditorError):
    """Exception raised when article processing fails."""
    
    def __init__(self, message: str, session_id: str = None, chunk_index: int = None, original_error: Exception = None):
        self.session_id = session_id
        self.chunk_index = chunk_index
        self.original_error = original_error
        super().__init__(message)


class BatchProcessingError(ArticleEditorError):
    """Exception raised when batch processing fails."""
    
    def __init__(self, message: str, failed_files: list = None, original_error: Exception = None):
        self.failed_files = failed_files or []
        self.original_error = original_error
        super().__init__(message)


class ConfigurationError(ArticleEditorError):
    """Exception raised when configuration is invalid."""
    pass


class WebSocketError(ArticleEditorError):
    """Exception raised when WebSocket communication fails."""
    
    def __init__(self, message: str, session_id: str = None, original_error: Exception = None):
        self.session_id = session_id
        self.original_error = original_error
        super().__init__(message)


class SessionError(ArticleEditorError):
    """Exception raised when session management fails."""
    
    def __init__(self, message: str, session_id: str = None, original_error: Exception = None):
        self.session_id = session_id
        self.original_error = original_error
        super().__init__(message)


class StorageError(ArticleEditorError):
    """Exception raised when file storage operations fail."""
    
    def __init__(self, message: str, file_path: str = None, operation: str = None, original_error: Exception = None):
        self.file_path = file_path
        self.operation = operation
        self.original_error = original_error
        super().__init__(message)


# Error handler utilities
def handle_api_error(error: Exception) -> APIError:
    """Convert various API errors to our custom APIError types."""
    import anthropic
    
    if isinstance(error, anthropic.RateLimitError):
        return RateLimitError(
            message=str(error),
            retry_after=getattr(error, 'retry_after', None),
            original_error=error
        )
    elif isinstance(error, anthropic.AuthenticationError):
        return AuthenticationError(original_error=error)
    elif isinstance(error, anthropic.BadRequestError):
        if "model" in str(error).lower():
            model_name = "unknown"
            return ModelNotAvailableError(model_name, original_error=error)
        else:
            return APIError(str(error), "bad_request", original_error=error)
    elif isinstance(error, anthropic.APIError):
        return APIError(str(error), "api_error", original_error=error)
    else:
        return APIError(f"Unexpected API error: {str(error)}", "unknown", original_error=error)


def handle_file_error(error: Exception, file_path: str = None) -> FileProcessingError:
    """Convert various file errors to our custom FileProcessingError types."""
    if isinstance(error, FileNotFoundError):
        return FileProcessingError(f"File not found: {file_path or 'unknown'}", file_path, error)
    elif isinstance(error, PermissionError):
        return FileProcessingError(f"Permission denied: {file_path or 'unknown'}", file_path, error)
    elif isinstance(error, UnicodeDecodeError):
        return FileValidationError(f"File encoding error: {file_path or 'unknown'}", file_path, error)
    elif "docx" in str(error).lower() or "python-docx" in str(error).lower():
        return UnsupportedFileFormatError(f"DOCX processing error: {str(error)}", file_path, error)
    else:
        return FileProcessingError(f"File processing error: {str(error)}", file_path, error)


def get_error_context(error: Exception) -> dict:
    """Extract context information from an error for logging."""
    context = {
        "error_type": type(error).__name__,
        "error_message": str(error)
    }
    
    # Add specific context based on error type
    if isinstance(error, FileProcessingError):
        context["file_path"] = getattr(error, "file_path", None)
    
    if isinstance(error, ChunkingError):
        context["chunk_index"] = getattr(error, "chunk_index", None)
    
    if isinstance(error, APIError):
        context["api_error_type"] = getattr(error, "error_type", None)
        context["retry_after"] = getattr(error, "retry_after", None)
    
    if isinstance(error, ProcessingError):
        context["session_id"] = getattr(error, "session_id", None)
        context["chunk_index"] = getattr(error, "chunk_index", None)
    
    if isinstance(error, BatchProcessingError):
        context["failed_files_count"] = len(getattr(error, "failed_files", []))
    
    # Add original error context if available
    if hasattr(error, "original_error") and error.original_error:
        context["original_error_type"] = type(error.original_error).__name__
        context["original_error_message"] = str(error.original_error)
    
    return context