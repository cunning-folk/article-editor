"""
Article processing engine that coordinates chunking, editing, and reassembly.
"""

import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import json
import os

from .chunker import TextChunker
from ..api.claude_client import ClaudeClient
from ..utils.file_handler import FileHandler


class ArticleProcessor:
    """Main processor for handling large article editing workflow."""
    
    def __init__(self, 
                 api_key: str,
                 model: str = "claude-3-5-sonnet-20241022",
                 chunk_size: int = 15000,
                 overlap: int = 500):
        self.chunker = TextChunker(chunk_size, overlap, model)
        self.claude_client = ClaudeClient(api_key, model)
        self.file_handler = FileHandler()
        self.logger = logging.getLogger(__name__)
        
        # Processing state
        self.current_session = None
        self.progress_callback = None
        
    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """Set callback function for progress updates: callback(current, total, message)"""
        self.progress_callback = callback
    
    def _update_progress(self, current: int, total: int, message: str = ""):
        """Update progress if callback is set."""
        if self.progress_callback:
            self.progress_callback(current, total, message)
    
    def process_article(self, 
                       input_path: str,
                       output_path: Optional[str] = None,
                       instructions: Optional[str] = None,
                       preview_only: bool = False,
                       create_backup: bool = True) -> Dict[str, Any]:
        """
        Process an article file with Claude editing.
        
        Args:
            input_path: Path to input file
            output_path: Path for output file (optional)
            instructions: Custom editing instructions
            preview_only: Only process first chunk for preview
            create_backup: Create backup of original file
            
        Returns:
            Dictionary with processing results and metadata
        """
        try:
            # Initialize session
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_session = {
                "id": session_id,
                "input_path": input_path,
                "output_path": output_path,
                "start_time": datetime.now(),
                "token_usage": {"input": 0, "output": 0},
                "chunks_processed": 0,
                "total_chunks": 0,
                "errors": []
            }
            
            self.logger.info(f"Starting article processing session {session_id}")
            
            # Read and validate input file
            self._update_progress(0, 100, "Reading input file...")
            original_text = self.file_handler.read_file(input_path)
            
            if not original_text.strip():
                raise ValueError("Input file is empty or contains no readable text")
            
            # Create backup if requested
            if create_backup:
                backup_path = self._create_backup(input_path)
                self.current_session["backup_path"] = backup_path
            
            # Prepare instructions
            edit_instructions = instructions or self._get_default_instructions()
            
            # Chunk the text
            self._update_progress(10, 100, "Analyzing and chunking text...")
            chunks = self.chunker.create_chunks_with_overlap(original_text)
            self.current_session["total_chunks"] = len(chunks)
            
            if preview_only:
                chunks = chunks[:1]
            
            self.logger.info(f"Split article into {len(chunks)} chunks")
            
            # Process chunks
            edited_chunks = []
            total_input_tokens = 0
            total_output_tokens = 0
            
            for i, (chunk_text, start_pos, end_pos) in enumerate(chunks):
                progress = 10 + int((i / len(chunks)) * 80)
                self._update_progress(progress, 100, f"Processing chunk {i+1}/{len(chunks)}...")
                
                try:
                    # Edit chunk with Claude
                    result = self.claude_client.edit_text(chunk_text, edit_instructions)
                    edited_chunks.append(result["edited_text"])
                    
                    # Track token usage
                    total_input_tokens += result["usage"]["input_tokens"]
                    total_output_tokens += result["usage"]["output_tokens"]
                    
                    self.current_session["chunks_processed"] += 1
                    
                except Exception as e:
                    error_msg = f"Error processing chunk {i+1}: {str(e)}"
                    self.logger.error(error_msg)
                    self.current_session["errors"].append(error_msg)
                    
                    # Use original chunk if editing fails
                    edited_chunks.append(chunk_text)
            
            # Reassemble edited text
            self._update_progress(90, 100, "Reassembling edited text...")
            edited_text = self.chunker.reassemble_chunks(edited_chunks)
            
            # Save output
            if not preview_only:
                output_file = output_path or self._generate_output_path(input_path)
                self.file_handler.write_file(output_file, edited_text)
                self.current_session["output_path"] = output_file
            
            # Finalize session
            self.current_session["end_time"] = datetime.now()
            self.current_session["token_usage"]["input"] = total_input_tokens
            self.current_session["token_usage"]["output"] = total_output_tokens
            self.current_session["cost_estimate"] = self._calculate_cost(total_input_tokens, total_output_tokens)
            
            self._update_progress(100, 100, "Processing complete!")
            
            return {
                "success": True,
                "session": self.current_session,
                "original_text": original_text if preview_only else None,
                "edited_text": edited_text,
                "chunks_count": len(chunks),
                "token_usage": self.current_session["token_usage"],
                "cost_estimate": self.current_session["cost_estimate"],
                "errors": self.current_session["errors"]
            }
            
        except Exception as e:
            error_msg = f"Article processing failed: {str(e)}"
            self.logger.error(error_msg)
            
            if self.current_session:
                self.current_session["errors"].append(error_msg)
                self.current_session["end_time"] = datetime.now()
            
            return {
                "success": False,
                "error": error_msg,
                "session": self.current_session
            }
    
    def _create_backup(self, input_path: str) -> str:
        """Create a backup of the original file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{input_path}.backup_{timestamp}"
        
        import shutil
        shutil.copy2(input_path, backup_path)
        
        self.logger.info(f"Created backup: {backup_path}")
        return backup_path
    
    def _generate_output_path(self, input_path: str) -> str:
        """Generate output path based on input path."""
        base, ext = os.path.splitext(input_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{base}_edited_{timestamp}{ext}"
    
    def _get_default_instructions(self) -> str:
        """Get default editing instructions."""
        return """Please edit this text with the following guidelines:
- Fix grammar, punctuation, and spelling errors
- Improve sentence flow and readability
- Ensure consistent tone and style throughout
- Fix awkward phrasing and unclear expressions
- Maintain the original meaning and voice
- Preserve formatting markers (headers, lists, etc.)
- Make the text more engaging and professional while keeping the author's intent

Provide only the edited text without any explanatory comments."""
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost based on token usage."""
        # Claude 3.5 Sonnet pricing (as of 2024)
        input_cost_per_1k = 0.003  # $3 per million tokens
        output_cost_per_1k = 0.015  # $15 per million tokens
        
        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (output_tokens / 1000) * output_cost_per_1k
        
        return round(input_cost + output_cost, 6)
    
    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get current session information."""
        return self.current_session
    
    def save_session_log(self, log_path: str):
        """Save session information to a log file."""
        if not self.current_session:
            return
        
        log_data = {
            **self.current_session,
            "start_time": self.current_session["start_time"].isoformat(),
            "end_time": self.current_session["end_time"].isoformat() if self.current_session.get("end_time") else None
        }
        
        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)