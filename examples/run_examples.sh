#!/bin/bash

# Article Editor Examples Script
# This script demonstrates various usage patterns of the Article Editor

echo "🚀 Article Editor Examples"
echo "=========================="

# Check if API key is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY environment variable is not set"
    echo "Please set your API key: export ANTHROPIC_API_KEY='your-key-here'"
    exit 1
fi

echo "✅ API key found"

# Create directories
mkdir -p example_outputs
mkdir -p batch_example/input
mkdir -p batch_example/output

# Create sample files for batch processing
echo "Creating sample files for batch processing..."

cat > batch_example/input/article1.txt << 'EOF'
Climate change is one of the most pressing issue's facing our planet today. The scientific consensus is clear: human activities are driving unprecedented changes in our climate system. Rising global temperatures, melting ice sheets, and more frequent extreme weather events are just some of the visible signs of this crisis.

The primary cause of climate change is the emission of greenhouse gases, particularly carbon dioxide, from burning fossil fuels. These gases trap heat in the atmosphere, leading to what scientists call the greenhouse effect. While this is a natural process that makes Earth habitable, human activities have intensified it to dangerous levels.

To address this challenge, we need immediate action on multiple fronts: transitioning to renewable energy, improving energy efficiency, and developing new technologies to capture and store carbon. Individual actions, while important, must be complemented by systemic changes in policy and industry.
EOF

cat > batch_example/input/article2.md << 'EOF'
# The Digital Revolution and Its Impact on Society

The digital revolution has transformed virtually every aspect of modern life. From how we communicate and work to how we shop and entertain ourselves, digital technologies have reshaped our world in ways that would have been unimaginable just a few decades ago.

## Communication and Social Interaction

Social media platforms have fundamentally changed how people connect and share information. While these platforms have made it easier to stay in touch with friends and family, they have also created new challenges around privacy, misinformation, and mental health.

## Economic Implications

The digital economy has created new business models and disrupted traditional industries. E-commerce has revolutionized retail, while the gig economy has changed the nature of work for millions of people.

## Future Considerations

As we move forward, it's crucial to consider both the benefits and risks of continued digital transformation. Issues like digital inequality, cybersecurity, and the ethical use of artificial intelligence will need careful attention.
EOF

echo "📝 Sample files created"

echo ""
echo "Example 1: Basic article editing with preview"
echo "============================================="
python ../src/cli/main.py -i sample_article.txt --preview --verbose

echo ""
echo "Example 2: Article editing with custom instructions"
echo "=================================================="
python ../src/cli/main.py -i sample_article.txt -o example_outputs/formal_article.txt \
    --instructions "Make the writing more formal and academic. Use precise technical language and ensure all claims are presented objectively."

echo ""
echo "Example 3: Article editing with different chunk settings"
echo "======================================================="
python ../src/cli/main.py -i sample_article.txt -o example_outputs/chunked_article.txt \
    --chunk-size 10000 --overlap 1000 --model claude-3-haiku-20240307

echo ""
echo "Example 4: File validation only"
echo "==============================="
python ../src/cli/main.py -i sample_article.txt --validate-only

echo ""
echo "Example 5: Cost estimation"
echo "========================="
python ../src/cli/main.py -i sample_article.txt --cost-estimate

echo ""
echo "Example 6: Batch processing from directory"
echo "=========================================="
python ../src/cli/batch.py --directory batch_example/input --output batch_example/output \
    --instructions "Improve clarity and readability while maintaining the original tone"

echo ""
echo "Example 7: Batch processing specific files"
echo "=========================================="
python ../src/cli/batch.py --files sample_article.txt batch_example/input/article1.txt \
    --output example_outputs --validate-only

echo ""
echo "Example 8: Batch processing with cost estimation"
echo "==============================================="
python ../src/cli/batch.py --directory batch_example/input --estimate-cost

echo ""
echo "Example 9: Web interface demo"
echo "============================"
echo "To test the web interface:"
echo "1. Start the server: python ../src/web/app.py"
echo "2. Open http://localhost:8000 in your browser"
echo "3. Upload sample_article.txt and process it"

echo ""
echo "🎉 Examples completed!"
echo "Check the 'example_outputs' and 'batch_example/output' directories for results."
echo ""
echo "Additional commands to try:"
echo "- View logs: tail -f ../logs/article_editor.log"
echo "- Clean up: rm -rf example_outputs batch_example ../logs ../uploads ../outputs"