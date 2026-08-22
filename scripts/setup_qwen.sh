#!/bin/bash

# Setup Qwen model for RAG system
# Usage: bash scripts/setup_qwen.sh [model_size]
# Examples: bash scripts/setup_qwen.sh 7b
#           bash scripts/setup_qwen.sh 32b
#           bash scripts/setup_qwen.sh 2.5-7b

MODEL_SIZE=${1:-7b}
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "================================================"
echo "Qwen Model Setup for RAG System"
echo "================================================"
echo ""

# Step 1: Download Qwen model
echo "[1/4] Downloading Qwen-${MODEL_SIZE}..."
ollama pull "qwen:${MODEL_SIZE}"

if [ $? -ne 0 ]; then
    echo "Error: Failed to download Qwen-${MODEL_SIZE}"
    echo "Make sure Ollama is installed: https://ollama.ai"
    exit 1
fi

echo "✓ Qwen-${MODEL_SIZE} downloaded"
echo ""

# Step 2: Update .env file
echo "[2/4] Updating configuration..."
cd "$PROJECT_DIR"

# Create or update .env
if [ ! -f .env ]; then
    cp .env.example .env
fi

# Update LLM_MODEL setting (works with both GNU and BSD sed)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/LLM_MODEL=.*/LLM_MODEL=qwen:${MODEL_SIZE}/" .env
else
    # Linux
    sed -i "s/LLM_MODEL=.*/LLM_MODEL=qwen:${MODEL_SIZE}/" .env
fi

echo "✓ Updated .env: LLM_MODEL=qwen:${MODEL_SIZE}"
echo ""

# Step 3: Verify model is available
echo "[3/4] Verifying installation..."
INSTALLED=$(ollama list | grep -c "qwen:${MODEL_SIZE}")

if [ $INSTALLED -eq 0 ]; then
    echo "⚠ Warning: Qwen-${MODEL_SIZE} not found in ollama list"
    echo "Checking available models..."
    ollama list | grep qwen
else
    echo "✓ Qwen-${MODEL_SIZE} is installed and ready"
fi

echo ""

# Step 4: Show next steps
echo "[4/4] Next Steps"
echo "================================================"
echo ""
echo "1. Start Docker services:"
echo "   docker-compose up -d"
echo ""
echo "2. Generate training data:"
echo "   python scripts/download_training_data.py"
echo ""
echo "3. Process data into chunks:"
echo "   python scripts/chunk_and_prepare_data.py"
echo ""
echo "4. Start the RAG system:"
echo "   python -m uvicorn src.main:app --reload"
echo ""
echo "5. Test with a query:"
echo "   curl -X POST 'http://localhost:8000/api/v1/default-tenant/query' \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"query\": \"What is health insurance?\"}'"
echo ""
echo "================================================"
echo "✓ Qwen-${MODEL_SIZE} setup complete!"
echo "================================================"
