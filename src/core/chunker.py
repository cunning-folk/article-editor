"""
Smart text chunking module for processing large articles.
Handles intelligent splitting while preserving context and boundaries.
"""

import re
from typing import List, Tuple
import tiktoken


class TextChunker:
    """Intelligent text chunker that respects paragraph and sentence boundaries."""
    
    def __init__(self, max_tokens: int = 15000, overlap_tokens: int = 500, model: str = "claude-3-5-sonnet-20241022"):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.model = model
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.encoding.encode(text))
    
    def split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs, preserving formatting."""
        paragraphs = re.split(r'\n\s*\n', text.strip())
        return [p.strip() for p in paragraphs if p.strip()]
    
    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using regex."""
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def create_chunks_with_overlap(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Create chunks with intelligent overlap to maintain context.
        Returns list of tuples: (chunk_text, start_char, end_char)
        """
        if self.count_tokens(text) <= self.max_tokens:
            return [(text, 0, len(text))]
        
        chunks = []
        paragraphs = self.split_into_paragraphs(text)
        
        current_chunk = ""
        current_start = 0
        char_position = 0
        
        for i, paragraph in enumerate(paragraphs):
            # Calculate token count if we add this paragraph
            test_chunk = current_chunk + ("\n\n" if current_chunk else "") + paragraph
            
            if self.count_tokens(test_chunk) > self.max_tokens and current_chunk:
                # Save current chunk
                chunks.append((current_chunk.strip(), current_start, char_position))
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = overlap_text + ("\n\n" if overlap_text else "") + paragraph
                current_start = char_position - len(overlap_text)
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n"
                    char_position += 2
                current_chunk += paragraph
            
            char_position += len(paragraph)
            if i < len(paragraphs) - 1:
                char_position += 2  # Account for double newlines
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append((current_chunk.strip(), current_start, char_position))
        
        return chunks
    
    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text from the end of current chunk."""
        if not text or self.overlap_tokens <= 0:
            return ""
        
        # Try to get overlap by sentences first
        sentences = self.split_into_sentences(text)
        overlap_text = ""
        
        for sentence in reversed(sentences):
            test_overlap = sentence + (" " if overlap_text else "") + overlap_text
            if self.count_tokens(test_overlap) <= self.overlap_tokens:
                overlap_text = test_overlap
            else:
                break
        
        # If no sentences fit, truncate by tokens
        if not overlap_text:
            words = text.split()
            for i in range(len(words)):
                test_text = " ".join(words[-(i+1):])
                if self.count_tokens(test_text) <= self.overlap_tokens:
                    overlap_text = test_text
                else:
                    break
        
        return overlap_text
    
    def reassemble_chunks(self, edited_chunks: List[str]) -> str:
        """Reassemble edited chunks, removing overlap."""
        if not edited_chunks:
            return ""
        
        if len(edited_chunks) == 1:
            return edited_chunks[0]
        
        result = edited_chunks[0]
        
        for i in range(1, len(edited_chunks)):
            current_chunk = edited_chunks[i]
            
            # Try to detect and remove overlap
            overlap_removed = self._remove_overlap(result, current_chunk)
            result += "\n\n" + overlap_removed
        
        return result.strip()
    
    def _remove_overlap(self, previous_text: str, current_chunk: str) -> str:
        """Attempt to remove overlap between chunks."""
        # Simple approach: look for common ending/beginning sequences
        prev_sentences = self.split_into_sentences(previous_text)
        curr_sentences = self.split_into_sentences(current_chunk)
        
        if not prev_sentences or not curr_sentences:
            return current_chunk
        
        # Find longest matching sequence at end of prev and start of curr
        max_overlap = min(3, len(prev_sentences), len(curr_sentences))
        
        for overlap_len in range(max_overlap, 0, -1):
            if prev_sentences[-overlap_len:] == curr_sentences[:overlap_len]:
                # Remove overlap from current chunk
                remaining_sentences = curr_sentences[overlap_len:]
                return " ".join(remaining_sentences)
        
        return current_chunk