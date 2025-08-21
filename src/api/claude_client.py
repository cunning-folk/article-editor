"""
Claude API client with rate limiting and error handling.
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
import anthropic
from anthropic import APIError, RateLimitError, APIConnectionError


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 50
    tokens_per_minute: int = 100000
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0


class ClaudeClient:
    """Claude API client with intelligent rate limiting and error handling."""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting state
        self.rate_config = RateLimitConfig()
        self.request_times = []
        self.token_usage_times = []
        
        # Validate API key on initialization
        self._validate_api_key()
    
    def _validate_api_key(self):
        """Validate API key by making a small test request."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            self.logger.info("API key validated successfully")
        except Exception as e:
            self.logger.error(f"API key validation failed: {e}")
            raise ValueError("Invalid API key or connection error")
    
    def _wait_for_rate_limit(self, estimated_tokens: int = 0):
        """Wait if necessary to respect rate limits."""
        current_time = time.time()
        
        # Clean old request times (older than 1 minute)
        cutoff_time = current_time - 60
        self.request_times = [t for t in self.request_times if t > cutoff_time]
        self.token_usage_times = [(t, tokens) for t, tokens in self.token_usage_times if t > cutoff_time]
        
        # Check request rate limit
        if len(self.request_times) >= self.rate_config.requests_per_minute:
            wait_time = 60 - (current_time - self.request_times[0])
            if wait_time > 0:
                self.logger.info(f"Rate limit reached, waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)
        
        # Check token rate limit
        total_tokens = sum(tokens for _, tokens in self.token_usage_times) + estimated_tokens
        if total_tokens >= self.rate_config.tokens_per_minute:
            wait_time = 60 - (current_time - self.token_usage_times[0][0])
            if wait_time > 0:
                self.logger.info(f"Token rate limit reached, waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)
        
        # Record this request
        self.request_times.append(current_time)
    
    def _exponential_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        delay = self.rate_config.base_delay * (2 ** attempt)
        return min(delay, self.rate_config.max_delay)
    
    def edit_text(self, text: str, instructions: str) -> Dict[str, Any]:
        """
        Edit text using Claude API with retry logic.
        
        Args:
            text: Text to edit
            instructions: Editing instructions
            
        Returns:
            Dictionary with edited text and metadata
        """
        estimated_tokens = len(text.split()) * 1.3  # Rough estimation
        
        for attempt in range(self.rate_config.max_retries):
            try:
                # Wait for rate limits
                self._wait_for_rate_limit(int(estimated_tokens))
                
                # Prepare the prompt
                prompt = f"{instructions}\n\nText to edit:\n{text}"
                
                # Make API call
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=min(100000, int(estimated_tokens * 1.5)),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1
                )
                
                # Record token usage
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                self.token_usage_times.append((time.time(), input_tokens + output_tokens))
                
                edited_text = response.content[0].text.strip()
                
                self.logger.info(f"Successfully edited text chunk ({input_tokens} input, {output_tokens} output tokens)")
                
                return {
                    "edited_text": edited_text,
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens
                    },
                    "model": self.model,
                    "attempt": attempt + 1
                }
                
            except RateLimitError as e:
                self.logger.warning(f"Rate limit hit on attempt {attempt + 1}: {e}")
                if attempt < self.rate_config.max_retries - 1:
                    delay = self._exponential_backoff(attempt)
                    self.logger.info(f"Waiting {delay} seconds before retry")
                    time.sleep(delay)
                else:
                    raise
                    
            except APIConnectionError as e:
                self.logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
                if attempt < self.rate_config.max_retries - 1:
                    delay = self._exponential_backoff(attempt)
                    self.logger.info(f"Waiting {delay} seconds before retry")
                    time.sleep(delay)
                else:
                    raise
                    
            except APIError as e:
                self.logger.error(f"API error on attempt {attempt + 1}: {e}")
                if attempt < self.rate_config.max_retries - 1 and "overloaded" in str(e).lower():
                    delay = self._exponential_backoff(attempt)
                    self.logger.info(f"API overloaded, waiting {delay} seconds before retry")
                    time.sleep(delay)
                else:
                    raise
                    
            except Exception as e:
                self.logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                raise
        
        raise Exception(f"Failed to edit text after {self.rate_config.max_retries} attempts")
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        current_time = time.time()
        cutoff_time = current_time - 60
        
        recent_requests = [t for t in self.request_times if t > cutoff_time]
        recent_tokens = sum(tokens for t, tokens in self.token_usage_times if t > cutoff_time)
        
        return {
            "requests_used": len(recent_requests),
            "requests_limit": self.rate_config.requests_per_minute,
            "tokens_used": recent_tokens,
            "tokens_limit": self.rate_config.tokens_per_minute,
            "next_reset": max(self.request_times + [t for t, _ in self.token_usage_times]) + 60 if (self.request_times or self.token_usage_times) else current_time
        }


class AsyncClaudeClient(ClaudeClient):
    """Async version of Claude client for web interface."""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        super().__init__(api_key, model)
        self.async_client = anthropic.AsyncAnthropic(api_key=api_key)
    
    async def edit_text_async(self, text: str, instructions: str) -> Dict[str, Any]:
        """Async version of edit_text method."""
        estimated_tokens = len(text.split()) * 1.3
        
        for attempt in range(self.rate_config.max_retries):
            try:
                # Wait for rate limits (simplified for async)
                await asyncio.sleep(0.1)  # Small delay to prevent overwhelming
                
                prompt = f"{instructions}\n\nText to edit:\n{text}"
                
                response = await self.async_client.messages.create(
                    model=self.model,
                    max_tokens=min(100000, int(estimated_tokens * 1.5)),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1
                )
                
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                edited_text = response.content[0].text.strip()
                
                return {
                    "edited_text": edited_text,
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens
                    },
                    "model": self.model,
                    "attempt": attempt + 1
                }
                
            except (RateLimitError, APIConnectionError) as e:
                if attempt < self.rate_config.max_retries - 1:
                    delay = self._exponential_backoff(attempt)
                    await asyncio.sleep(delay)
                else:
                    raise
                    
            except Exception as e:
                self.logger.error(f"Async edit error: {e}")
                raise
        
        raise Exception(f"Failed to edit text after {self.rate_config.max_retries} attempts")