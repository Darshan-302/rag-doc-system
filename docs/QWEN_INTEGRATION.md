# Qwen Model Integration Guide

Complete guide to using Qwen open-weight models in your RAG system.

---

## 🤖 Available Qwen Models

### Qwen Model Lineup

| Model | Params | Context | Speed | Quality | Memory | Use Case |
|-------|--------|---------|-------|---------|--------|----------|
| **Qwen-7B** | 7B | 32K | ⚡⚡⚡ | ⭐⭐⭐⭐ | 15GB | Fast, good quality |
| **Qwen-14B** | 14B | 32K | ⚡⚡ | ⭐⭐⭐⭐ | 28GB | Balanced |
| **Qwen-32B** | 32B | 32K | ⚡ | ⭐⭐⭐⭐⭐ | 65GB | Best quality |
| **Qwen-72B** | 72B | 32K | 🐌 | ⭐⭐⭐⭐⭐ | 145GB | Enterprise |
| **Qwen2.5-7B** | 7B | 128K | ⚡⚡⚡ | ⭐⭐⭐⭐ | 15GB | Latest, fast |
| **Qwen2.5-32B** | 32B | 128K | ⚡ | ⭐⭐⭐⭐⭐ | 65GB | Latest, best |

### ⭐ Recommended for RAG
- **Best balance**: **Qwen2.5-7B** (15GB RAM, fast, good quality)
- **Best quality**: **Qwen-32B** or **Qwen2.5-32B** (65GB RAM)
- **Lightweight**: **Qwen-7B** (fits on RTX 3090)

**Note**: There's no "Qwen 3.8 27B" - you probably mean one of the above. The closest is **Qwen-32B** (32B parameters) or **Qwen-7B** (7B parameters).

---

## 📥 Download Qwen Models

### Option 1: Using Ollama (Easiest)

```bash
# Install Ollama if not already done
# https://ollama.ai

# Download Qwen-7B
ollama pull qwen:7b

# Or Qwen-32B
ollama pull qwen:32b

# Or latest Qwen2.5
ollama pull qwen2.5:7b
ollama pull qwen2.5:32b

# Verify installation
ollama list
```

### Option 2: Using Hugging Face (More Control)

```bash
# Install HF CLI
pip install huggingface-hub

# Download Qwen-7B
huggingface-cli download Qwen/Qwen-7B --local-dir ./models/qwen-7b

# Download Qwen-32B
huggingface-cli download Qwen/Qwen-32B --local-dir ./models/qwen-32b

# Download latest Qwen2.5
huggingface-cli download Qwen/Qwen2.5-7B --local-dir ./models/qwen2.5-7b
```

### Option 3: Using HF Transformers

```python
from transformers import AutoTokenizer, AutoModelForCausalLM

# Download and load Qwen-7B
model_name = "Qwen/Qwen-7B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    torch_dtype="auto"
)

# Now ready to use
inputs = tokenizer("What is health insurance?", return_tensors="pt")
outputs = model.generate(**inputs, max_length=512)
print(tokenizer.decode(outputs[0]))
```

---

## ⚙️ Configure Your RAG System for Qwen

### Step 1: Update `.env` File

```env
# Old (Mistral)
# LLM_MODEL=mistral:latest

# New (Qwen)
LLM_MODEL=qwen:7b              # or qwen:32b, qwen2.5:7b, etc.
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text:latest

# Qwen-specific settings
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2048            # Qwen can handle larger outputs
LLM_TOP_P=0.9

# Performance tuning
EMBEDDING_BATCH_SIZE=128
```

### Step 2: Update Configuration File

Edit `src/config.py`:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # LLM Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen:7b"  # Change to Qwen
    EMBEDDING_MODEL: str = "nomic-embed-text:latest"
    
    # Qwen Inference Parameters
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2048      # Qwen supports 32K context
    LLM_TOP_P: float = 0.9
    
    # For Qwen-specific features
    QWEN_REPETITION_PENALTY: float = 1.0
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### Step 3: Test Configuration

```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags

# Should show your Qwen model
# Response: {"models": [{"name": "qwen:7b", ...}]}
```

---

## 🚀 Complete Setup for Qwen

### Step-by-Step

```bash
# 1. Navigate to repo
cd /Users/darshan/darshan-patel/rag-system-repo

# 2. Update .env for Qwen
cat > .env << 'EOF'
DATABASE_URL=postgresql://rag_user:rag_password@localhost:5432/rag_db
REDIS_URL=redis://localhost:6379
WEAVIATE_URL=http://localhost:8080
OLLAMA_BASE_URL=http://localhost:11434

# Use Qwen instead of Mistral
LLM_MODEL=qwen:7b
EMBEDDING_MODEL=nomic-embed-text:latest

LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2048
LLM_TOP_P=0.9

CHUNK_SIZE=512
CHUNK_OVERLAP=50
TOP_K_DOCUMENTS=5
EOF

# 3. Download Qwen model
ollama pull qwen:7b

# 4. Start services
docker-compose up -d

# 5. Generate training data
python scripts/download_training_data.py

# 6. Process into chunks
python scripts/chunk_and_prepare_data.py

# 7. Run your RAG
python -m uvicorn src.main:app --reload

# 8. Test with Qwen
curl -X POST "http://localhost:8000/api/v1/default-tenant/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is health insurance?"}'
```

---

## 💻 Performance: Qwen vs Mistral

### Qwen-7B vs Mistral-7B

| Metric | Qwen-7B | Mistral-7B | Winner |
|--------|---------|-----------|--------|
| **Size** | 15GB | 15GB | Tie |
| **Speed** | 3 tokens/sec | 3 tokens/sec | Tie |
| **Quality on Insurance Q** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Tie |
| **Chinese support** | Excellent | Poor | Qwen ✅ |
| **Instruction-following** | Excellent | Excellent | Tie |
| **License** | Apache 2.0 | Apache 2.0 | Tie |

### Qwen-32B vs Mistral-7B

| Metric | Qwen-32B | Mistral-7B |
|--------|----------|-----------|
| **Quality** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Speed** | 1 token/sec | 3 tokens/sec |
| **Memory** | 65GB | 15GB |
| **Best for** | Quality-first | Speed-first |

---

## 🎯 Hardware Requirements by Model

### Qwen-7B
```
Minimum: RTX 3090 (24GB)
Recommended: RTX 4090 (24GB)
Or: Single A10 (24GB)
```

### Qwen-32B
```
Minimum: 2x A100 40GB (distributed inference)
Or: H100 (80GB)
Recommended: 2x H100 (distributed)
```

### Qwen2.5-7B (Latest)
```
Minimum: RTX 3060 (12GB) - tight
Recommended: RTX 4090 (24GB)
Great with: vLLM for 10x speedup
```

---

## 🔧 Advanced: Quantized Qwen Models

For smaller GPUs, use quantized versions:

```bash
# 4-bit quantized Qwen-7B (fits in 8GB RAM)
ollama pull qwen:7b-q4_K_M

# 3-bit quantized (fits in 4GB RAM)
ollama pull qwen:7b-q3_K_M

# Use in .env
LLM_MODEL=qwen:7b-q4_K_M
```

**Trade-off**: Smaller memory, slightly lower quality

---

## 🧠 Using Qwen with vLLM (10x Faster)

For production deployments, use vLLM for 10x faster inference:

```bash
# Install vLLM
pip install vllm

# Create inference server
python << 'EOF'
from vllm import LLM, SamplingParams

# Load Qwen-7B with vLLM
llm = LLM(
    model="Qwen/Qwen-7B",
    tensor_parallel_size=1,  # or 2 for dual GPU
    max_model_len=32000
)

# Batch inference
prompts = [
    "What is health insurance?",
    "What are pre-existing conditions?",
    "How do insurance claims work?"
]

sampling_params = SamplingParams(
    temperature=0.7,
    top_p=0.9,
    max_tokens=2048
)

outputs = llm.generate(prompts, sampling_params)

for output in outputs:
    print(output.outputs[0].text)
EOF
```

---

## 📋 Prompt Template for Qwen

Qwen works best with its native chat format:

```python
def create_qwen_prompt(query: str, context: str) -> str:
    """Create prompt optimized for Qwen."""
    
    prompt = f"""You are a helpful healthcare and insurance assistant.
Answer the user's question based only on the provided documents.

Documents:
{context}

Question: {query}

Answer:"""
    
    return prompt
```

Or use Qwen's chat format:

```python
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen-7B", trust_remote_code=True)

messages = [
    {
        "role": "system",
        "content": "You are a helpful healthcare assistant. Answer based on documents provided."
    },
    {
        "role": "user",
        "content": f"Documents: {context}\n\nQuestion: {query}"
    }
]

text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)

# Use text in model.generate()
```

---

## ✅ Implementation Checklist

- [ ] Downloaded Qwen model (`ollama pull qwen:7b`)
- [ ] Updated `.env` with `LLM_MODEL=qwen:7b`
- [ ] Updated `src/config.py` with Qwen settings
- [ ] Started Docker services (`docker-compose up -d`)
- [ ] Generated training data (`python scripts/download_training_data.py`)
- [ ] Processed chunks (`python scripts/chunk_and_prepare_data.py`)
- [ ] Started API (`python -m uvicorn src.main:app --reload`)
- [ ] Tested query with Qwen model

---

## 🎯 Which Qwen to Choose?

| Your Situation | Recommendation | Reason |
|---|---|---|
| **Testing locally, limited GPU** | Qwen-7B | Fast, good quality, 15GB |
| **Production, best quality** | Qwen-32B or Qwen2.5-32B | Excellent quality, 65GB |
| **Limited RAM (< 16GB)** | Qwen-7B-q4 (quantized) | Fits in 8GB, good quality |
| **Need speed, quality OK** | Qwen-7B with vLLM | 10x faster than standard |
| **Enterprise, no GPU limit** | Qwen-72B | Best quality possible |

---

## 🔗 Resources

- **Qwen Models**: https://huggingface.co/Qwen
- **Qwen Docs**: https://qwenlm.github.io/
- **Ollama Qwen**: https://ollama.ai/library/qwen
- **GitHub**: https://github.com/QwenLM/Qwen

---

## ⚡ Quick Start (Copy-Paste)

```bash
# 1. Download Qwen-7B
ollama pull qwen:7b

# 2. Update config
echo 'LLM_MODEL=qwen:7b' >> .env

# 3. Restart services
docker-compose restart

# 4. Test immediately
curl -X POST "http://localhost:8000/api/v1/default-tenant/query" \
  -d '{"query": "What is health insurance?"}'
```

**That's it! Your RAG now uses Qwen.**

---

## 🚀 Next Steps

1. Choose your Qwen model based on GPU
2. Download with Ollama
3. Update `.env` file
4. Restart your RAG system
5. All queries now use Qwen!

**Need help with GPU setup? Let me know which GPU you have and I'll optimize it.**
