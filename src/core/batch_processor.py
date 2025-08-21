"""
Batch processing functionality for multiple files.
"""

import asyncio
import os
import logging
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from datetime import datetime
import json
import concurrent.futures
from dataclasses import dataclass

from .processor import ArticleProcessor
from ..utils.file_handler import FileHandler


@dataclass
class BatchJob:
    """Represents a single file in a batch processing job."""
    file_path: str
    output_path: Optional[str] = None
    status: str = "pending"  # pending, processing, completed, failed
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    token_usage: Optional[Dict[str, int]] = None
    cost_estimate: Optional[float] = None


class BatchProcessor:
    """Handles batch processing of multiple articles."""
    
    def __init__(self, 
                 api_key: str,
                 model: str = "claude-3-5-sonnet-20241022",
                 chunk_size: int = 15000,
                 overlap: int = 500,
                 max_workers: int = 3):
        self.api_key = api_key
        self.model = model
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)
        self.file_handler = FileHandler()
        
        # Batch state
        self.current_batch = None
        self.progress_callback = None
        self.is_processing = False
        
    def set_progress_callback(self, callback: Callable[[int, int, str, List[BatchJob]], None]):
        """Set callback for progress updates: callback(completed, total, message, jobs)"""
        self.progress_callback = callback
    
    def _update_progress(self, completed: int, total: int, message: str = "", jobs: List[BatchJob] = None):
        """Update progress if callback is set."""
        if self.progress_callback:
            self.progress_callback(completed, total, message, jobs or [])
    
    def create_batch_from_directory(self, 
                                  directory: str, 
                                  output_directory: Optional[str] = None,
                                  file_patterns: List[str] = None) -> List[BatchJob]:
        """
        Create a batch job from all supported files in a directory.
        
        Args:
            directory: Input directory path
            output_directory: Output directory (optional)
            file_patterns: File patterns to match (e.g., ['*.txt', '*.md'])
            
        Returns:
            List of BatchJob objects
        """
        if not os.path.exists(directory):
            raise ValueError(f"Directory does not exist: {directory}")
        
        # Default patterns for supported file types
        if file_patterns is None:
            file_patterns = ['*.txt', '*.md', '*.docx', '*.doc']
        
        jobs = []
        input_path = Path(directory)
        
        # Find all matching files
        for pattern in file_patterns:
            for file_path in input_path.glob(pattern):
                if file_path.is_file():
                    # Generate output path
                    if output_directory:
                        output_dir = Path(output_directory)
                        output_dir.mkdir(parents=True, exist_ok=True)
                        output_path = output_dir / f"{file_path.stem}_edited{file_path.suffix}"
                    else:
                        output_path = file_path.parent / f"{file_path.stem}_edited{file_path.suffix}"
                    
                    jobs.append(BatchJob(
                        file_path=str(file_path),
                        output_path=str(output_path)
                    ))
        
        self.logger.info(f"Created batch with {len(jobs)} files from {directory}")
        return jobs
    
    def create_batch_from_file_list(self, 
                                   file_paths: List[str],
                                   output_directory: Optional[str] = None) -> List[BatchJob]:
        """
        Create a batch job from a list of file paths.
        
        Args:
            file_paths: List of input file paths
            output_directory: Output directory (optional)
            
        Returns:
            List of BatchJob objects
        """
        jobs = []
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                self.logger.warning(f"File does not exist, skipping: {file_path}")
                continue
            
            # Validate file
            try:
                validation = self.file_handler.validate_file(file_path)
                if not validation["valid"]:
                    self.logger.warning(f"Invalid file, skipping: {file_path} - {validation['errors']}")
                    continue
            except Exception as e:
                self.logger.warning(f"Error validating file, skipping: {file_path} - {e}")
                continue
            
            # Generate output path
            input_file = Path(file_path)
            if output_directory:
                output_dir = Path(output_directory)
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"{input_file.stem}_edited{input_file.suffix}"
            else:
                output_path = input_file.parent / f"{input_file.stem}_edited{input_file.suffix}"
            
            jobs.append(BatchJob(
                file_path=file_path,
                output_path=str(output_path)
            ))
        
        self.logger.info(f"Created batch with {len(jobs)} files from file list")
        return jobs
    
    def validate_batch(self, jobs: List[BatchJob]) -> Dict[str, Any]:
        """
        Validate all files in a batch and estimate costs.
        
        Args:
            jobs: List of batch jobs
            
        Returns:
            Validation results with cost estimates
        """
        valid_jobs = []
        invalid_jobs = []
        total_words = 0
        total_estimated_cost = 0
        
        for job in jobs:
            try:
                validation = self.file_handler.validate_file(job.file_path)
                
                if validation["valid"]:
                    valid_jobs.append(job)
                    
                    # Add to cost estimation
                    if validation["info"].get("word_count"):
                        words = validation["info"]["word_count"]
                        total_words += words
                        
                        # Estimate tokens and cost
                        estimated_tokens = words * 1.3
                        estimated_cost = (estimated_tokens / 1000) * 0.003 + (estimated_tokens / 1000) * 0.015
                        total_estimated_cost += estimated_cost
                        
                else:
                    invalid_jobs.append({
                        "file_path": job.file_path,
                        "errors": validation["errors"]
                    })
                    
            except Exception as e:
                invalid_jobs.append({
                    "file_path": job.file_path,
                    "errors": [str(e)]
                })
        
        return {
            "valid_count": len(valid_jobs),
            "invalid_count": len(invalid_jobs),
            "invalid_files": invalid_jobs,
            "total_words": total_words,
            "estimated_cost": total_estimated_cost,
            "estimated_processing_time": len(valid_jobs) * 30  # Rough estimate: 30 seconds per file
        }
    
    def process_batch(self, 
                     jobs: List[BatchJob],
                     instructions: Optional[str] = None,
                     continue_on_error: bool = True) -> Dict[str, Any]:
        """
        Process a batch of files.
        
        Args:
            jobs: List of batch jobs
            instructions: Custom editing instructions
            continue_on_error: Whether to continue processing if a file fails
            
        Returns:
            Batch processing results
        """
        if self.is_processing:
            raise RuntimeError("Batch processing already in progress")
        
        self.is_processing = True
        self.current_batch = {
            "jobs": jobs,
            "start_time": datetime.now(),
            "completed_count": 0,
            "failed_count": 0,
            "total_token_usage": {"input": 0, "output": 0},
            "total_cost": 0.0
        }
        
        try:
            self.logger.info(f"Starting batch processing of {len(jobs)} files")
            self._update_progress(0, len(jobs), "Starting batch processing...", jobs)
            
            # Process files with limited concurrency
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                
                for job in jobs:
                    future = executor.submit(self._process_single_file, job, instructions)
                    futures.append(future)
                
                # Wait for completion and update progress
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
                    try:
                        result = future.result()
                        
                        # Update job status
                        job = result["job"]
                        if result["success"]:
                            job.status = "completed"
                            job.token_usage = result.get("token_usage")
                            job.cost_estimate = result.get("cost_estimate")
                            self.current_batch["completed_count"] += 1
                            
                            # Update totals
                            if job.token_usage:
                                self.current_batch["total_token_usage"]["input"] += job.token_usage["input"]
                                self.current_batch["total_token_usage"]["output"] += job.token_usage["output"]
                            
                            if job.cost_estimate:
                                self.current_batch["total_cost"] += job.cost_estimate
                                
                        else:
                            job.status = "failed"
                            job.error_message = result.get("error", "Unknown error")
                            self.current_batch["failed_count"] += 1
                            
                            if not continue_on_error:
                                self.logger.error(f"Stopping batch due to error: {job.error_message}")
                                break
                        
                        job.end_time = datetime.now()
                        
                        # Update progress
                        completed = self.current_batch["completed_count"] + self.current_batch["failed_count"]
                        self._update_progress(
                            completed, 
                            len(jobs), 
                            f"Processed {completed}/{len(jobs)} files", 
                            jobs
                        )
                        
                    except Exception as e:
                        self.logger.error(f"Error processing file: {e}")
                        self.current_batch["failed_count"] += 1
            
            self.current_batch["end_time"] = datetime.now()
            self.logger.info(f"Batch processing completed: {self.current_batch['completed_count']} successful, {self.current_batch['failed_count']} failed")
            
            return {
                "success": True,
                "completed_count": self.current_batch["completed_count"],
                "failed_count": self.current_batch["failed_count"],
                "total_files": len(jobs),
                "total_token_usage": self.current_batch["total_token_usage"],
                "total_cost": self.current_batch["total_cost"],
                "processing_time": (self.current_batch["end_time"] - self.current_batch["start_time"]).total_seconds(),
                "jobs": jobs
            }
            
        except Exception as e:
            self.logger.error(f"Batch processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "jobs": jobs
            }
            
        finally:
            self.is_processing = False
    
    def _process_single_file(self, job: BatchJob, instructions: Optional[str]) -> Dict[str, Any]:
        """Process a single file in the batch."""
        job.start_time = datetime.now()
        job.status = "processing"
        
        try:
            # Create processor for this file
            processor = ArticleProcessor(
                api_key=self.api_key,
                model=self.model,
                chunk_size=self.chunk_size,
                overlap=self.overlap
            )
            
            # Process the file
            result = processor.process_article(
                input_path=job.file_path,
                output_path=job.output_path,
                instructions=instructions,
                preview_only=False,
                create_backup=False
            )
            
            if result["success"]:
                return {
                    "success": True,
                    "job": job,
                    "token_usage": result["token_usage"],
                    "cost_estimate": result["cost_estimate"]
                }
            else:
                return {
                    "success": False,
                    "job": job,
                    "error": result["error"]
                }
                
        except Exception as e:
            return {
                "success": False,
                "job": job,
                "error": str(e)
            }
    
    def save_batch_report(self, result: Dict[str, Any], report_path: str):
        """Save batch processing report to file."""
        report_data = {
            "batch_summary": {
                "total_files": result["total_files"],
                "completed_count": result["completed_count"],
                "failed_count": result["failed_count"],
                "success_rate": result["completed_count"] / result["total_files"] * 100,
                "total_cost": result["total_cost"],
                "processing_time_seconds": result.get("processing_time", 0)
            },
            "jobs": []
        }
        
        # Add job details
        for job in result["jobs"]:
            job_data = {
                "file_path": job.file_path,
                "output_path": job.output_path,
                "status": job.status,
                "start_time": job.start_time.isoformat() if job.start_time else None,
                "end_time": job.end_time.isoformat() if job.end_time else None,
                "token_usage": job.token_usage,
                "cost_estimate": job.cost_estimate,
                "error_message": job.error_message
            }
            report_data["jobs"].append(job_data)
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        self.logger.info(f"Batch report saved to: {report_path}")
    
    def get_batch_status(self) -> Optional[Dict[str, Any]]:
        """Get current batch processing status."""
        if not self.current_batch:
            return None
        
        return {
            "is_processing": self.is_processing,
            "start_time": self.current_batch["start_time"],
            "completed_count": self.current_batch["completed_count"],
            "failed_count": self.current_batch["failed_count"],
            "total_files": len(self.current_batch["jobs"]),
            "progress_percentage": ((self.current_batch["completed_count"] + self.current_batch["failed_count"]) / len(self.current_batch["jobs"])) * 100,
            "total_cost": self.current_batch["total_cost"],
            "jobs": self.current_batch["jobs"]
        }