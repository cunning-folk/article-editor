# Article Editor

A powerful, production-ready Python application that uses Claude AI to intelligently edit large articles with support for multiple formats, smart chunking, and both command-line and web interfaces.

## 🌟 Features

### Core Functionality
- **Smart Text Chunking**: Intelligently splits large documents while preserving context and paragraph boundaries
- **Multiple Format Support**: Handles .txt, .md, and .docx files seamlessly
- **Context Preservation**: Maintains document flow with configurable overlap between chunks
- **Rate Limiting**: Built-in API rate limiting with exponential backoff for reliable processing
- **Cost Estimation**: Accurate token counting and cost estimation before processing

### Editing Capabilities
- **Comprehensive Editing**: Grammar, style, clarity, and flow improvements
- **Custom Instructions**: Flexible editing guidelines for specific needs
- **Multiple AI Models**: Support for Claude 3.5 Sonnet, Haiku, and Opus
- **Batch Processing**: Process multiple files simultaneously with progress tracking
- **Preview Mode**: Test editing on first chunk before processing entire document

### User Interfaces
- **Command Line Interface**: Full-featured CLI with progress indicators
- **Modern Web Interface**: Responsive web UI with real-time progress updates
- **Batch Processing Tools**: Dedicated tools for processing multiple files
- **REST API**: Complete FastAPI backend for integration

### Enterprise Features
- **Comprehensive Logging**: Detailed logging with session tracking
- **Error Handling**: Robust error handling with graceful recovery
- **Configuration Management**: Flexible configuration via files and environment variables
- **Session Management**: Track processing history and download results
- **Security**: Input validation, file type checking, and secure uploads

## 🚀 Quick Start

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd article_editor
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up your API key:**
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### Command Line Usage

**Basic editing:**
```bash
python src/cli/main.py -i document.txt
```

**Custom instructions:**
```bash
python src/cli/main.py -i article.md -o edited_article.md --instructions "Make the tone more formal and academic"
```

**Preview mode:**
```bash
python src/cli/main.py -i draft.txt --preview
```

**Batch processing:**
```bash
python src/cli/batch.py --directory ./documents --output ./edited_documents
```

### Web Interface

1. **Start the web server:**
```bash
python src/web/app.py
```

2. **Open your browser:**
Navigate to `http://localhost:8000`

3. **Upload and process:**
- Drag and drop your document
- Configure editing options
- Monitor real-time progress
- Download the edited result

## 📋 Command Line Reference

### Single File Processing

```bash
python src/cli/main.py [OPTIONS]
```

**Required Arguments:**
- `-i, --input`: Input file path

**Optional Arguments:**
- `-o, --output`: Output file path (auto-generated if not specified)
- `--instructions`: Custom editing instructions
- `--chunk-size`: Maximum tokens per chunk (default: 15000)
- `--overlap`: Overlap tokens between chunks (default: 500)
- `--model`: Claude model to use (default: claude-3-5-sonnet-20241022)
- `--preview`: Preview first chunk only
- `--no-backup`: Skip creating backup of original file
- `--validate-only`: Only validate the input file
- `--cost-estimate`: Show cost estimate before processing
- `--verbose`: Enable verbose logging

### Batch Processing

```bash
python src/cli/batch.py [OPTIONS]
```

**Input Options (choose one):**
- `--directory DIR`: Process all files in directory
- `--files FILE [FILE ...]`: Process specific files

**Processing Options:**
- `--output DIR`: Output directory
- `--pattern PATTERN`: File patterns to match (e.g., "*.md")
- `--instructions TEXT`: Custom editing instructions
- `--max-workers N`: Maximum concurrent workers (default: 3)
- `--continue-on-error`: Continue if individual files fail

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Your Claude API key | Required |
| `ARTICLE_EDITOR_MODEL` | Default AI model | claude-3-5-sonnet-20241022 |
| `ARTICLE_EDITOR_CHUNK_SIZE` | Default chunk size | 15000 |
| `ARTICLE_EDITOR_OVERLAP` | Default overlap size | 500 |
| `ARTICLE_EDITOR_HOST` | Web server host | 0.0.0.0 |
| `ARTICLE_EDITOR_PORT` | Web server port | 8000 |
| `ARTICLE_EDITOR_LOG_LEVEL` | Logging level | INFO |

### Configuration File

Create `config.json` in the project root:

```json
{
  \"model\": {
    \"name\": \"claude-3-5-sonnet-20241022\",
    \"max_tokens\": 100000,
    \"temperature\": 0.1
  },
  \"chunking\": {
    \"default_chunk_size\": 15000,
    \"default_overlap\": 500
  },
  \"web\": {
    \"host\": \"0.0.0.0\",
    \"port\": 8000,
    \"max_file_size\": 52428800
  },
  \"logging\": {
    \"level\": \"INFO\",
    \"log_dir\": \"logs\"
  }
}
```

## 🌐 Web API Documentation

### Endpoints

**File Upload:**
```http
POST /api/upload
Content-Type: multipart/form-data

Response: {"file_id": "...", "filename": "...", "file_info": {...}}
```

**Start Processing:**
```http
POST /api/process
Content-Type: application/x-www-form-urlencoded

Parameters:
- file_id: Uploaded file ID
- instructions: Editing instructions
- chunk_size: Chunk size in tokens
- overlap: Overlap size in tokens
- model: AI model to use
- preview_only: Boolean for preview mode
```

**WebSocket Updates:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/session_id');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Handle progress updates
};
```

**Download Result:**
```http
GET /api/download/session_id
Response: File download
```

## 🏗️ Architecture

### Core Components

```
article_editor/
├── src/
│   ├── core/              # Core processing logic
│   │   ├── processor.py   # Main article processor
│   │   ├── chunker.py     # Smart text chunking
│   │   └── batch_processor.py  # Batch processing
│   ├── api/               # API clients
│   │   └── claude_client.py    # Claude API wrapper
│   ├── cli/               # Command line interfaces
│   │   ├── main.py        # Single file CLI
│   │   └── batch.py       # Batch processing CLI
│   ├── web/               # Web application
│   │   └── app.py         # FastAPI application
│   └── utils/             # Utilities
│       ├── file_handler.py     # File I/O operations
│       ├── logger.py           # Logging system
│       └── exceptions.py       # Custom exceptions
├── web/                   # Web interface files
│   ├── templates/         # HTML templates
│   └── static/           # CSS, JS, assets
└── config.py             # Configuration management
```

### Processing Flow

1. **File Upload & Validation**: Check format, size, and readability
2. **Smart Chunking**: Split text while preserving context
3. **AI Processing**: Send chunks to Claude with consistent instructions
4. **Reassembly**: Merge edited chunks with overlap removal
5. **Output Generation**: Save processed document with metadata

## 📊 Performance & Costs

### Token Usage

- **Input tokens**: Original text + instructions for each chunk
- **Output tokens**: Edited text returned by Claude
- **Overlap handling**: Minimizes redundant processing

### Cost Estimates (Claude 3.5 Sonnet)

| Document Size | Estimated Tokens | Estimated Cost |
|---------------|------------------|----------------|
| 1,000 words | ~1,300 tokens | ~$0.02 |
| 5,000 words | ~6,500 tokens | ~$0.12 |
| 10,000 words | ~13,000 tokens | ~$0.23 |
| 50,000 words | ~65,000 tokens | ~$1.17 |

*Costs are estimates and may vary based on actual token usage and model pricing.*

### Performance Tips

- **Optimize chunk size**: Larger chunks reduce API calls but may hit token limits
- **Use overlap wisely**: Balance context preservation with processing efficiency
- **Batch processing**: Process multiple files concurrently for better throughput
- **Choose appropriate model**: Use Haiku for speed, Sonnet for balance, Opus for quality

## 🔍 Troubleshooting

### Common Issues

**API Key Error:**
```
Error: Invalid API key or authentication failed
```
*Solution*: Verify your `ANTHROPIC_API_KEY` environment variable is set correctly.

**File Format Error:**
```
Error: Unsupported file format
```
*Solution*: Ensure file is .txt, .md, or .docx format. For .docx files, install `python-docx`.

**Rate Limit Error:**
```
Error: Rate limit exceeded
```
*Solution*: The application automatically handles rate limits with exponential backoff. Large documents may take longer to process.

**Memory Issues:**
```
Error: Out of memory
```
*Solution*: Reduce chunk size or process files individually instead of batch processing.

### Debugging

**Enable verbose logging:**
```bash
python src/cli/main.py -i document.txt --verbose
```

**Check log files:**
```bash
tail -f logs/article_editor.log
tail -f logs/errors.log
```

**Validate file before processing:**
```bash
python src/cli/main.py -i document.txt --validate-only
```

## 🧪 Testing

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

### Manual Testing

**Test with sample document:**
```bash
echo "This is a test document with some grammar error's and awkward phrasing that need to be fixed." > test.txt
python src/cli/main.py -i test.txt --preview
```

**Test web interface:**
1. Start the web server
2. Upload the test document
3. Use preview mode to verify functionality

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes with appropriate tests
4. Ensure code passes linting: `black src/ && flake8 src/`
5. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install black flake8 mypy pytest pytest-asyncio

# Run code formatting
black src/

# Run linting
flake8 src/

# Run type checking
mypy src/
```

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: See this README and inline code documentation
- **Issues**: Report bugs and request features via GitHub Issues
- **API Reference**: Claude API documentation at [docs.anthropic.com](https://docs.anthropic.com)

## 🔮 Roadmap

- [ ] Support for additional file formats (PDF, RTF)
- [ ] Integration with popular writing tools (Google Docs, Notion)
- [ ] Advanced diff visualization in web interface
- [ ] Plugin system for custom editing rules
- [ ] Desktop application with Electron
- [ ] Integration with version control systems
- [ ] Collaborative editing features
- [ ] Advanced analytics and reporting

---

**Article Editor** - Intelligent document editing powered by Claude AI