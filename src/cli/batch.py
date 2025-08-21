#!/usr/bin/env python3
"""
Batch processing command-line interface for the Article Editor.
"""

import argparse
import sys
import os
import json
from pathlib import Path
from typing import List

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.batch_processor import BatchProcessor
from src.utils.logger import setup_logging, get_logger
from src.utils.file_handler import FileHandler


def get_api_key() -> str:
    """Get API key from environment or prompt user."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        api_key = input("Please enter your Anthropic API key: ").strip()
        if not api_key:
            print("Error: API key is required")
            sys.exit(1)
    return api_key


def progress_callback(completed: int, total: int, message: str, jobs: List):
    """Progress callback for batch processing."""
    if total > 0:
        percentage = (completed / total) * 100
        bar_length = 40
        filled_length = int(bar_length * completed // total)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        print(f'\r[{bar}] {percentage:.1f}% ({completed}/{total}) {message}', end='', flush=True)
        if completed == total:
            print()  # New line when complete


def print_job_summary(jobs: List):
    """Print summary of batch jobs."""
    total = len(jobs)
    completed = sum(1 for job in jobs if job.status == "completed")
    failed = sum(1 for job in jobs if job.status == "failed")
    
    print(f"\n📊 Batch Summary:")
    print(f"  • Total files: {total}")
    print(f"  • Completed: {completed}")
    print(f"  • Failed: {failed}")
    print(f"  • Success rate: {(completed/total)*100:.1f}%" if total > 0 else "  • Success rate: 0%")
    
    # Show failed files
    if failed > 0:
        print(f"\n❌ Failed files:")
        for job in jobs:
            if job.status == "failed":
                print(f"  • {job.file_path}: {job.error_message}")
    
    # Show token usage and costs
    total_input_tokens = sum(job.token_usage["input"] if job.token_usage else 0 for job in jobs)
    total_output_tokens = sum(job.token_usage["output"] if job.token_usage else 0 for job in jobs)
    total_cost = sum(job.cost_estimate if job.cost_estimate else 0 for job in jobs)
    
    if total_input_tokens > 0:
        print(f"\n💰 Resource Usage:")
        print(f"  • Input tokens: {total_input_tokens:,}")
        print(f"  • Output tokens: {total_output_tokens:,}")
        print(f"  • Total cost: ${total_cost:.6f}")


def main():
    """Main batch processing function."""
    parser = argparse.ArgumentParser(
        description="Batch process multiple articles using Claude AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  article-editor-batch --directory ./documents --output ./edited_documents
  article-editor-batch --files doc1.txt doc2.md doc3.docx --output ./output
  article-editor-batch --directory ./articles --pattern "*.md" --instructions "Make more formal"
  article-editor-batch --files *.txt --validate-only
        """
    )
    
    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--directory', '-d',
        help='Directory containing files to process'
    )
    input_group.add_argument(
        '--files', '-f',
        nargs='+',
        help='List of specific files to process'
    )
    
    # Output options
    parser.add_argument(
        '--output', '-o',
        help='Output directory (default: same as input with _edited suffix)'
    )
    
    # Pattern matching (only for directory mode)
    parser.add_argument(
        '--pattern', '-p',
        nargs='+',
        default=['*.txt', '*.md', '*.docx'],
        help='File patterns to match (default: *.txt *.md *.docx)'
    )
    
    # Processing options
    parser.add_argument(
        '--instructions', '-inst',
        help='Custom editing instructions'
    )
    
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=15000,
        help='Maximum tokens per chunk (default: 15000)'
    )
    
    parser.add_argument(
        '--overlap',
        type=int,
        default=500,
        help='Overlap tokens between chunks (default: 500)'
    )
    
    parser.add_argument(
        '--model',
        default='claude-3-5-sonnet-20241022',
        help='Claude model to use (default: claude-3-5-sonnet-20241022)'
    )
    
    parser.add_argument(
        '--max-workers',
        type=int,
        default=3,
        help='Maximum concurrent processing workers (default: 3)'
    )
    
    # Control options
    parser.add_argument(
        '--continue-on-error',
        action='store_true',
        help='Continue processing other files if one fails'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate files without processing'
    )
    
    parser.add_argument(
        '--estimate-cost',
        action='store_true',
        help='Show cost estimate before processing'
    )
    
    parser.add_argument(
        '--save-report',
        help='Save detailed report to JSON file'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(log_level="DEBUG" if args.verbose else "INFO")
    logger = get_logger(__name__)
    
    try:
        # Get API key
        api_key = get_api_key()
        
        # Initialize batch processor
        processor = BatchProcessor(
            api_key=api_key,
            model=args.model,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
            max_workers=args.max_workers
        )
        
        # Set progress callback
        processor.set_progress_callback(progress_callback)
        
        # Create batch jobs
        print("🔍 Scanning for files...")
        
        if args.directory:
            jobs = processor.create_batch_from_directory(
                args.directory,
                args.output,
                args.pattern
            )
        else:
            jobs = processor.create_batch_from_file_list(
                args.files,
                args.output
            )
        
        if not jobs:
            print("❌ No valid files found to process")
            sys.exit(1)
        
        print(f"✅ Found {len(jobs)} files to process")
        
        # Validate batch
        print("🔍 Validating files...")
        validation = processor.validate_batch(jobs)
        
        print(f"✅ Validation complete:")
        print(f"  • Valid files: {validation['valid_count']}")
        print(f"  • Invalid files: {validation['invalid_count']}")
        print(f"  • Total words: {validation['total_words']:,}")
        print(f"  • Estimated cost: ${validation['estimated_cost']:.6f}")
        print(f"  • Estimated time: {validation['estimated_processing_time']} seconds")
        
        if validation['invalid_files']:
            print(f"\n⚠️  Invalid files:")
            for invalid_file in validation['invalid_files']:
                print(f"  • {invalid_file['file_path']}: {', '.join(invalid_file['errors'])}")
        
        if args.validate_only:
            print("Validation complete.")
            return
        
        if validation['valid_count'] == 0:
            print("❌ No valid files to process")
            sys.exit(1)
        
        # Cost confirmation
        if args.estimate_cost or validation['estimated_cost'] > 1.0:
            print(f"\n💰 Estimated cost: ${validation['estimated_cost']:.6f}")
            if not args.estimate_cost:
                response = input("Continue with batch processing? (y/N): ").strip().lower()
                if response != 'y':
                    print("Batch processing cancelled.")
                    return
            else:
                return
        
        # Process batch
        print(f"\n🚀 Starting batch processing of {validation['valid_count']} files...")
        print(f"  • Model: {args.model}")
        print(f"  • Chunk size: {args.chunk_size} tokens")
        print(f"  • Overlap: {args.overlap} tokens")
        print(f"  • Max workers: {args.max_workers}")
        print(f"  • Continue on error: {args.continue_on_error}")
        print()
        
        result = processor.process_batch(
            jobs,
            instructions=args.instructions,
            continue_on_error=args.continue_on_error
        )
        
        if result["success"]:
            print("\n✅ Batch processing completed!")
            print_job_summary(jobs)
            
            # Save report if requested
            if args.save_report:
                processor.save_batch_report(result, args.save_report)
                print(f"📄 Report saved to: {args.save_report}")
        
        else:
            print(f"\n❌ Batch processing failed: {result['error']}")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Batch processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()