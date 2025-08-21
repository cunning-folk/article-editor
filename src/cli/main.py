#!/usr/bin/env python3
"""
Command-line interface for the Article Editor.
"""

import argparse
import sys
import os
import logging
from typing import Optional
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.processor import ArticleProcessor
from src.utils.file_handler import FileHandler


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def get_api_key() -> str:
    """Get API key from environment or prompt user."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        api_key = input("Please enter your Anthropic API key: ").strip()
        if not api_key:
            print("Error: API key is required")
            sys.exit(1)
    return api_key


def progress_callback(current: int, total: int, message: str = ""):
    """Progress callback for CLI display."""
    if total > 0:
        percentage = (current / total) * 100
        bar_length = 40
        filled_length = int(bar_length * current // total)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        print(f'\r[{bar}] {percentage:.1f}% {message}', end='', flush=True)
        if current == total:
            print()  # New line when complete


def validate_arguments(args) -> bool:
    """Validate command line arguments."""
    # Check input file
    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' does not exist")
        return False
    
    # Validate chunk size
    if args.chunk_size < 1000:
        print("Error: Chunk size must be at least 1000 tokens")
        return False
    
    if args.chunk_size > 100000:
        print("Error: Chunk size cannot exceed 100000 tokens")
        return False
    
    # Validate overlap
    if args.overlap < 0:
        print("Error: Overlap cannot be negative")
        return False
    
    if args.overlap >= args.chunk_size:
        print("Error: Overlap must be smaller than chunk size")
        return False
    
    # Validate output path if provided
    if args.output:
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            print(f"Error: Output directory '{output_dir}' does not exist")
            return False
    
    return True


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Edit large articles using Claude AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  article_editor -i document.txt
  article_editor -i article.md -o edited_article.md --instructions "Make it more formal"
  article_editor -i report.docx --chunk-size 20000 --overlap 1000
  article_editor -i draft.txt --preview --model claude-3-haiku-20240307
        """
    )
    
    # Required arguments
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input file path (.txt, .md, .docx)'
    )
    
    # Optional arguments
    parser.add_argument(
        '-o', '--output',
        help='Output file path (default: auto-generated based on input)'
    )
    
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
        '--preview',
        action='store_true',
        help='Preview first chunk only (for testing)'
    )
    
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Skip creating backup of original file'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate the input file without processing'
    )
    
    parser.add_argument(
        '--cost-estimate',
        action='store_true',
        help='Show cost estimate before processing'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Validate arguments
    if not validate_arguments(args):
        sys.exit(1)
    
    try:
        # Initialize file handler for validation
        file_handler = FileHandler()
        
        # Validate input file
        print(f"Validating input file: {args.input}")
        validation = file_handler.validate_file(args.input)
        
        if not validation["valid"]:
            print("❌ File validation failed:")
            for error in validation["errors"]:
                print(f"  • {error}")
            sys.exit(1)
        
        if validation["warnings"]:
            print("⚠️  Warnings:")
            for warning in validation["warnings"]:
                print(f"  • {warning}")
        
        # Display file info
        info = validation["info"]
        print(f"✅ File validated successfully")
        print(f"  • Format: {info['extension']}")
        print(f"  • Size: {info['size_bytes']:,} bytes")
        if info["word_count"]:
            print(f"  • Words: {info['word_count']:,}")
            print(f"  • Characters: {info['char_count']:,}")
        
        if args.validate_only:
            print("Validation complete.")
            return
        
        # Get API key
        api_key = get_api_key()
        
        # Initialize processor
        processor = ArticleProcessor(
            api_key=api_key,
            model=args.model,
            chunk_size=args.chunk_size,
            overlap=args.overlap
        )
        
        # Set progress callback
        processor.set_progress_callback(progress_callback)
        
        # Cost estimation
        if args.cost_estimate or info.get("word_count", 0) > 10000:
            estimated_tokens = info.get("word_count", 0) * 1.3
            estimated_cost = (estimated_tokens / 1000) * 0.003 + (estimated_tokens / 1000) * 0.015
            print(f"\n💰 Estimated cost: ${estimated_cost:.4f}")
            
            if not args.cost_estimate:
                response = input("Continue with processing? (y/N): ").strip().lower()
                if response != 'y':
                    print("Processing cancelled.")
                    return
            else:
                return
        
        # Process the article
        print(f"\n🚀 Starting article processing...")
        print(f"  • Model: {args.model}")
        print(f"  • Chunk size: {args.chunk_size} tokens")
        print(f"  • Overlap: {args.overlap} tokens")
        print(f"  • Preview mode: {'Yes' if args.preview else 'No'}")
        print()
        
        result = processor.process_article(
            input_path=args.input,
            output_path=args.output,
            instructions=args.instructions,
            preview_only=args.preview,
            create_backup=not args.no_backup
        )
        
        if result["success"]:
            print("\n✅ Processing completed successfully!")
            
            # Display results
            session = result["session"]
            print(f"  • Chunks processed: {session['chunks_processed']}/{session['total_chunks']}")
            print(f"  • Token usage: {result['token_usage']['input']:,} input, {result['token_usage']['output']:,} output")
            print(f"  • Estimated cost: ${result['cost_estimate']:.6f}")
            
            if not args.preview:
                print(f"  • Output file: {session['output_path']}")
                if session.get('backup_path'):
                    print(f"  • Backup created: {session['backup_path']}")
            
            # Display any errors
            if result["errors"]:
                print("\n⚠️  Errors encountered:")
                for error in result["errors"]:
                    print(f"  • {error}")
            
            # Save session log
            if not args.preview:
                log_path = session["output_path"] + ".log"
                processor.save_session_log(log_path)
                print(f"  • Session log: {log_path}")
        
        else:
            print(f"\n❌ Processing failed: {result['error']}")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()