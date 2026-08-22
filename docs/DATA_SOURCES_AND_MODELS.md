# Open Data Sources & Open-Weight LLM Models for Insurance/Healthcare RAG

## 🎯 Strategy Overview

```
Training Data (Insurance/Health) → Chunking & Preprocessing → RAG System
                    ↓
            Open-Weight LLMs (7B-34B)
            - Llama 2/3, Mistral, Deepseek
            - No licensing costs, full control
```

---

## 📊 LEGITIMATE PUBLIC DATASETS FOR INSURANCE & HEALTHCARE

### 1. **Healthcare Datasets**

#### A. **NIH Clinical Trials Database** (Free, Public)
- **URL**: https://clinicaltrials.gov/api/query/full_studies
- **Content**: 400K+ clinical trial descriptions
- **Format**: XML/JSON
- **Size**: ~50GB
- **Use Case**: Healthcare protocols, treatment information
- **License**: Public Domain
- **How to use**:
```bash
# Download API data
curl "https://clinicaltrials.gov/api/query/full_studies?pageSize=1000&pageNumber=1" \
  -o trials.json

# Or use Python
import requests
response = requests.get(
    "https://clinicaltrials.gov/api/query/full_studies",
    params={"pageSize": 1000, "pageNumber": 1}
)
trials = response.json()["FullStudiesResponse"]["NStudiesReturned"]
```

#### B. **PubMed Central (PMC)** (Open Access)
- **URL**: https://www.ncbi.nlm.nih.gov/pmc/
- **Content**: 3M+ free full-text research articles
- **Format**: XML, PDF
- **Size**: ~200GB
- **Use Case**: Medical research, health conditions, treatments
- **License**: Open Access (CC-BY, CC0)
- **How to download**:
```bash
# Using NCBI FTP
wget -r ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/ --limit-rate=1m

# Or use PMC API
# https://www.ncbi.nlm.nih.gov/pmc/tools/openftlist/
```

#### C. **Medical MNIST Dataset** (Healthcare Images)
- **URL**: https://github.com/MedMNIST/MedMNIST
- **Content**: Medical imaging datasets (10 datasets)
- **Use Case**: Medical imaging RAG (with OCR of reports)
- **License**: CC-BY 4.0
- **Size**: ~10GB

#### D. **FDA Orange Book** (Drug Approvals)
- **URL**: https://www.fda.gov/drugs/drug-approvals-and-databases/approved-drugs
- **Content**: FDA-approved drugs, medical devices, indications
- **Format**: CSV, Web
- **Size**: ~500MB
- **Use Case**: Drug information, indications, contraindications
- **License**: Public Domain
- **Download**:
```python
# Scrape FDA Orange Book
import requests
from bs4 import BeautifulSoup

url = "https://www.fda.gov/cder/orange_book/txt/drug.txt"
response = requests.get(url)
drugs = response.text.split('\n')
# Parse and chunk
```

#### E. **MIMIC-III Dataset** (Patient Records)
- **URL**: https://mimic.physionet.org/
- **Content**: 61K hospital admissions, clinical notes, lab results
- **Format**: CSV
- **Size**: ~50GB (compressed)
- **License**: PhysioNet Credential Agreement (free access)
- **Use Case**: Clinical documentation, EMR data
- **How to access**:
  1. Register at https://physionet.org/
  2. Complete CITI training
  3. Request access to MIMIC-III
  4. Download via PhysioNet

#### F. **MedQA Dataset** (Medical Q&A)
- **URL**: https://github.com/jing-1066/MedQA
- **Content**: 47K medical exam Q&A
- **Format**: JSON
- **Size**: ~200MB
- **License**: MIT
- **Use Case**: Medical question answering training

---

### 2. **Insurance-Related Datasets**

#### A. **Insurance Policy Documents** (Open Sources)
- **US State Insurance Regulations**:
  - https://content.naic.org/ (National Association of Insurance Commissioners)
  - 50+ states insurance codes
  - Format: PDF/Text
  - Size: ~500MB
  - License: Public Domain

#### B. **Medicare Data**
- **URL**: https://www.cms.gov/data-research/tools-applications/cms-open-payments
- **Content**: Medicare claims data, provider info
- **Format**: CSV
- **Size**: ~10GB+
- **License**: Public Domain
- **How to use**:
```python
# Download Medicare provider data
import pandas as pd
url = "https://data.cms.gov/api/views/pde4-m7u6/rows.csv?accessType=DOWNLOAD"
df = pd.read_csv(url)
```

#### C. **NAIC Insurance Data**
- **URL**: https://www.naic.org/
- **Content**: Insurance company financial data, risk assessments
- **Format**: Excel, PDF
- **License**: Public (some restricted)
- **Size**: ~100MB

#### D. **World Health Organization (WHO) Data**
- **URL**: https://www.who.int/data
- **Content**: Health statistics, disease prevalence, mortality data
- **Format**: CSV, JSON
- **License**: CC-BY-4.0
- **Size**: ~500MB

#### E. **Insurance QA Datasets**
- **URL**: https://github.com/shuzi/insuranceQA
- **Content**: 23K insurance Q&A pairs
- **Format**: JSON
- **License**: Apache 2.0
- **Size**: ~50MB

---

### 3. **Compliance & Legal Documents** (For Insurance)

#### A. **Legislation & Regulations**
- **GDPR Text**: https://gdpr-info.eu/
- **HIPAA Regulations**: https://www.hhs.gov/hipaa/
- **Insurance Act Compilations**: Various state legislature sites
- **Format**: Text/PDF
- **License**: Public Domain

#### B. **Medical Textbooks (Open Access)**
- **OpenStax Biology**: https://openstax.org/details/books/biology-2e
- **OpenStax Anatomy & Physiology**: https://openstax.org/details/books/anatomy-and-physiology
- **License**: CC-BY 4.0
- **Format**: PDF, HTML
- **Size**: ~100MB each

---

## 🤖 OPEN-WEIGHT LLM MODELS (Best for Commercial RAG)

### Model Comparison Table

| Model | Params | Context | License | Speed | Quality | Recommended? |
|-------|--------|---------|---------|-------|---------|--------------|
| **Llama 3.1** | 8B / 70B | 128K | Llama 2 | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | ✅ Best overall |
| **Mistral 7B** | 7B | 32K | Apache 2.0 | ⚡⚡⚡ | ⭐⭐⭐⭐ | ✅ Fast & good |
| **Mistral Nemo** | 12B | 128K | Apache 2.0 | ⚡⚡ | ⭐⭐⭐⭐ | ✅ Great balance |
| **Deepseek-LLM** | 7B / 67B | 4K | MIT | ⚡⚡⚡ | ⭐⭐⭐⭐ | ✅ Emerging |
| **Phi-3** | 3.8B | 4K | MIT | ⚡⚡⚡⚡ | ⭐⭐⭐ | ✅ Very fast |
| **Qwen** | 7B / 32B | 128K | Apache 2.0 | ⚡⚡ | ⭐⭐⭐⭐ | ✅ Good |
| **Llama 2** | 7B / 13B / 70B | 4K | Llama 2 | ⚡⚡ | ⭐⭐⭐ | ⚠️ Older |

---

## 🎯 RECOMMENDED SETUP FOR INSURANCE/HEALTHCARE

### **Tier 1: Production (Recommended)**

```yaml
Model: Llama 3.1 70B or Mistral 7B
Context: 32K-128K tokens
License: Llama 2 / Apache 2.0 (fully open)
Speed: Optimized with vLLM/TGI
Cost: $0 (self-hosted)
GPU: 2x A100 40GB (for 70B) or RTX 4090 (for 7B)

Why: 
- Excellent instruction-following
- Large context for complex documents
- Fully open, no licensing restrictions
- Good domain performance (healthcare docs)
```

### **Tier 2: Fast/Lightweight**

```yaml
Model: Mistral 7B or Llama 3.1 8B
Context: 32K tokens
License: Apache 2.0
Speed: Fast (1-2 tokens/sec)
GPU: Single RTX 3090
Cost: $0

Why:
- Excellent speed for real-time RAG
- Fits on consumer GPUs
- Good accuracy for most use cases
```

### **Tier 3: Fast & Tiny**

```yaml
Model: Phi-3 or Mistral Nemo
Context: 4K-128K
License: MIT / Apache 2.0
Speed: Very fast (3-5 tokens/sec)
GPU: RTX 4060 or even CPU
Cost: $0

Why:
- Runs on laptops/edge devices
- Fast inference for demos
- Good for cost-sensitive deployments
```

---

## 📥 HOW TO DOWNLOAD & USE MODELS

### 1. **Download from Hugging Face** (Easiest)

```bash
# Install Ollama (includes model download)
# https://ollama.ai

# Download Llama 3.1
ollama pull llama2:70b

# Download Mistral
ollama pull mistral:latest

# Run locally
ollama run llama2:70b

# API endpoint: http://localhost:11434/api/generate
```

### 2. **Using Hugging Face Directly**

```python
from transformers import AutoTokenizer, AutoModelForCausalLM

# Download Llama 3.1 8B
model_id = "meta-llama/Llama-2-7b-hf"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="auto",  # Auto-detect GPU
    torch_dtype="auto"
)

# Generate
inputs = tokenizer("How does insurance work?", return_tensors="pt")
outputs = model.generate(**inputs, max_length=1024)
print(tokenizer.decode(outputs[0]))
```

### 3. **Using vLLM** (Fastest Inference)

```python
from vllm import LLM, SamplingParams

# Load model
llm = LLM(model="meta-llama/Llama-2-70b-hf", tensor_parallel_size=2)

# Batch inference
prompts = [
    "What is health insurance?",
    "What are pre-existing conditions?"
]

sampling_params = SamplingParams(temperature=0.7, max_tokens=512)
outputs = llm.generate(prompts, sampling_params)

for output in outputs:
    print(output.outputs[0].text)
```

### 4. **Download via Git LFS**

```bash
# Install git-lfs
brew install git-lfs  # or apt-get install git-lfs

# Clone model repo
git clone https://huggingface.co/meta-llama/Llama-2-70b-hf
cd Llama-2-70b-hf

# Large files download automatically
git lfs pull
```

---

## 🗂️ DATA PREPARATION PIPELINE

### Step 1: Collect Raw Data

```python
import requests
import pandas as pd
from pathlib import Path

# Create data directory
data_dir = Path("data/raw/insurance_healthcare")
data_dir.mkdir(parents=True, exist_ok=True)

# 1. Download FDA drug data
print("Downloading FDA drug data...")
url = "https://www.fda.gov/cder/orange_book/txt/drug.txt"
response = requests.get(url)
with open(data_dir / "fda_drugs.txt", "w") as f:
    f.write(response.text)

# 2. Download insurance QA dataset
print("Downloading InsuranceQA dataset...")
import json
url = "https://raw.githubusercontent.com/shuzi/insuranceQA/master/corpus/corpus"
for i in range(10):
    response = requests.get(f"{url}_{i}")
    data = json.loads(response.text)
    with open(data_dir / f"insurance_qa_{i}.json", "w") as f:
        json.dump(data, f)

# 3. Download NAIC insurance company data
print("Downloading NAIC data...")
# (Usually requires manual download or API access)

print(f"✓ Raw data downloaded to {data_dir}")
```

### Step 2: Parse & Clean

```python
import re
from pathlib import Path
import json

def clean_medical_text(text):
    """Clean medical text for RAG."""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep medical notation
    text = re.sub(r'[^\w\s\-\./()[\]°]', '', text)
    
    # Normalize medical abbreviations
    text = text.replace('Dr. ', 'Doctor ')
    text = text.replace('Rx ', 'Prescription ')
    
    return text.strip()

def parse_fda_drug_file(file_path):
    """Parse FDA drug text file."""
    drugs = []
    current_drug = {}
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith("APPL ID"):
                if current_drug:
                    drugs.append(current_drug)
                current_drug = {}
            elif line.startswith("DRUG NAME"):
                current_drug['name'] = line.split(":", 1)[1].strip()
            elif line.startswith("APPLICANT"):
                current_drug['company'] = line.split(":", 1)[1].strip()
    
    return drugs

# Process all files
raw_dir = Path("data/raw/insurance_healthcare")
processed_dir = Path("data/processed")
processed_dir.mkdir(parents=True, exist_ok=True)

# Parse FDA data
print("Parsing FDA drug data...")
drugs = parse_fda_drug_file(raw_dir / "fda_drugs.txt")
with open(processed_dir / "fda_drugs.json", "w") as f:
    json.dump(drugs, f, indent=2)

print(f"✓ Processed {len(drugs)} drugs")
```

### Step 3: Chunk for RAG

```python
from typing import List, Dict
import json

def chunk_documents(
    text: str,
    chunk_size: int = 512,
    overlap: int = 50
) -> List[str]:
    """Chunk text into overlapping chunks."""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    
    return chunks

def prepare_training_data(
    processed_dir: Path,
    output_file: Path,
    chunk_size: int = 512
) -> int:
    """Prepare chunked documents for RAG."""
    chunks_data = []
    doc_id = 0
    
    # Process FDA drugs
    with open(processed_dir / "fda_drugs.json") as f:
        drugs = json.load(f)
        for drug in drugs:
            text = f"Drug: {drug.get('name', '')}. Company: {drug.get('company', '')}"
            chunks = chunk_documents(text, chunk_size)
            
            for chunk_idx, chunk in enumerate(chunks):
                chunks_data.append({
                    "document_id": f"fda_{doc_id}",
                    "chunk_id": chunk_idx,
                    "text": chunk,
                    "source": "FDA Orange Book",
                    "metadata": {
                        "drug_name": drug.get('name'),
                        "company": drug.get('company')
                    }
                })
            doc_id += 1
    
    # Save chunks
    with open(output_file, "w") as f:
        json.dump(chunks_data, f, indent=2)
    
    return len(chunks_data)

# Run pipeline
total_chunks = prepare_training_data(
    processed_dir,
    Path("data/rag_training_data.json")
)
print(f"✓ Created {total_chunks} chunks for RAG training")
```

---

## 🔍 WHERE TO FIND MODELS

### **Model Hubs**

| Hub | URL | Models | License Diversity |
|-----|-----|--------|------------------|
| **Hugging Face** | https://huggingface.co/models | 500K+ | All types |
| **Ollama** | https://ollama.ai/library | 100+ | Mostly open |
| **Replicate** | https://replicate.com | 50K+ | Various |
| **AI Hub** | https://aihub.cloud | 1000+ | Various |
| **Together AI** | https://www.together.ai | 100+ | Open focus |

### **Direct Download**

```bash
# Llama 3.1 8B
huggingface-cli download meta-llama/Llama-2-8b-hf --local-dir ./models/llama-8b

# Mistral 7B
huggingface-cli download mistralai/Mistral-7B-v0.1 --local-dir ./models/mistral

# Qwen 7B
huggingface-cli download Qwen/Qwen-7B --local-dir ./models/qwen

# Deepseek 7B
huggingface-cli download deepseek-ai/deepseek-llm-7b-base --local-dir ./models/deepseek
```

---

## 💾 DATASET SIZE RECOMMENDATIONS

| RAG Use Case | Training Data Size | Chunked Size | Remarks |
|---|---|---|---|
| **MVP (Insurance FAQs)** | 100-500 documents | 1K-5K chunks | Start here |
| **Small Domain (One specialty)** | 1,000-5,000 docs | 10K-50K chunks | Good coverage |
| **Medium (Multi-domain)** | 10,000-50,000 docs | 100K-500K chunks | Most practical |
| **Enterprise (Full coverage)** | 100K+ docs | 1M+ chunks | Production-scale |

**Recommendation for you**: Start with **10-20K documents** (~100K chunks)
- Mix from: FDA data + Medical QA + Insurance regulations
- Enough diversity for good RAG performance
- Manageable to process locally

---

## 🔐 COMPLIANCE & LICENSING NOTES

### ✅ **Safe to Use (Public Domain / Open License)**
- FDA drug data
- Clinical trials.gov
- NAIC public filings
- OpenStax textbooks
- WHO data
- GitHub open datasets (check license)

### ⚠️ **Requires Registration/Agreement**
- MIMIC-III (free but need Physionet account + CITI training)
- Some HIPAA-restricted healthcare data

### ❌ **DO NOT USE (Proprietary/Protected)**
- Patient medical records (even de-identified without consent)
- Proprietary insurance company data
- Copyrighted medical textbooks
- Real healthcare claims data

### **Model Licensing for Commercial Use**

| Model | License | Can Use Commercially? |
|-------|---------|---|
| Llama 2/3 | Llama 2 / Llama 3 | ✅ Yes |
| Mistral | Apache 2.0 | ✅ Yes |
| Deepseek | MIT | ✅ Yes |
| Qwen | Apache 2.0 | ✅ Yes |
| GPT-4 | Proprietary | ❌ No (need API) |
| Claude | Proprietary | ❌ No (need API) |

---

## 📋 IMPLEMENTATION SCRIPT

Here's a complete script to set up your training data:

```python
#!/usr/bin/env python3
"""Download and prepare insurance/healthcare training data for RAG."""

import json
import requests
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataDownloader:
    def __init__(self, data_dir="data/raw"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def download_fda_drugs(self):
        """Download FDA Orange Book."""
        logger.info("Downloading FDA drugs...")
        url = "https://www.fda.gov/cder/orange_book/txt/drug.txt"
        response = requests.get(url)
        with open(self.data_dir / "fda_drugs.txt", "w") as f:
            f.write(response.text)
        logger.info("✓ FDA drugs downloaded")
    
    def download_insurance_qa(self):
        """Download InsuranceQA dataset."""
        logger.info("Downloading InsuranceQA...")
        url_base = "https://raw.githubusercontent.com/shuzi/insuranceQA/master"
        
        # Download corpus
        corpus_dir = self.data_dir / "insurance_qa_corpus"
        corpus_dir.mkdir(exist_ok=True)
        
        for i in range(5):  # First 5 files
            url = f"{url_base}/corpus/corpus_{i}"
            try:
                response = requests.get(url, timeout=10)
                with open(corpus_dir / f"corpus_{i}", "w") as f:
                    f.write(response.text)
                logger.info(f"  Downloaded corpus part {i}")
            except Exception as e:
                logger.warning(f"  Failed to download corpus {i}: {e}")
        
        logger.info("✓ InsuranceQA downloaded")
    
    def download_clinical_trials(self, num_pages=10):
        """Download clinical trials data."""
        logger.info("Downloading clinical trials...")
        trials = []
        
        for page in range(1, num_pages + 1):
            url = "https://clinicaltrials.gov/api/query/full_studies"
            params = {
                "pageSize": 100,
                "pageNumber": page,
                "fmt": "json"
            }
            
            try:
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                trials.extend(data.get("FullStudiesResponse", {}).get("NStudiesReturned", 0))
                logger.info(f"  Downloaded page {page}")
            except Exception as e:
                logger.warning(f"  Failed to download page {page}: {e}")
        
        # Save
        with open(self.data_dir / "clinical_trials.json", "w") as f:
            json.dump(trials, f)
        
        logger.info(f"✓ Downloaded {len(trials)} clinical trials")

if __name__ == "__main__":
    downloader = DataDownloader()
    
    # Download all sources
    downloader.download_fda_drugs()
    downloader.download_insurance_qa()
    downloader.download_clinical_trials()
    
    logger.info("\n✓ All data downloaded successfully!")
    logger.info(f"Data location: {downloader.data_dir}")
```

---

## 🚀 QUICK START FOR YOUR RAG

### Step 1: Download Models

```bash
# Use Ollama (easiest)
ollama pull llama2:70b      # or llama2:13b or llama2:7b
ollama pull nomic-embed-text:latest

# Or use vLLM for faster inference
pip install vllm
python -c "from vllm import LLM; LLM('meta-llama/Llama-2-7b-hf')"
```

### Step 2: Get Training Data

```bash
python scripts/download_training_data.py
```

### Step 3: Chunk & Index

```bash
python scripts/chunk_and_index.py \
  --input-dir data/raw \
  --output-dir data/processed \
  --chunk-size 512 \
  --chunk-overlap 50
```

### Step 4: Test RAG

```bash
python -m uvicorn src.main:app --reload
curl -X POST "http://localhost:8000/api/v1/default-tenant/query" \
  -d '{"query": "What is a pre-existing condition?"}'
```

---

## 📊 SUMMARY TABLE

| Resource | Type | Size | Cost | Effort | Recommendation |
|----------|------|------|------|--------|---|
| **FDA Orange Book** | Insurance/Drug | 500MB | Free | Easy | ✅ Start here |
| **Clinical Trials** | Health | 50GB | Free | Medium | ✅ Include |
| **PubMed Central** | Research | 200GB | Free | Hard | ⭐ Best quality |
| **MIMIC-III** | Clinical | 50GB | Free | Hard | ✅ For healthcare |
| **InsuranceQA** | Insurance | 50MB | Free | Easy | ✅ Include |
| **Llama 3.1** | Model | 70GB | Free | Medium | ✅ Use this |
| **Mistral 7B** | Model | 15GB | Free | Easy | ✅ Lighter option |

---

## 🎯 NEXT: Integration with Your RAG System

Once you have data, integrate it:

```python
# In your RAG pipeline
from pathlib import Path
from src.ingestion.document_processor import DocumentProcessor

processor = DocumentProcessor()
data_dir = Path("data/processed/insurance_healthcare")

# Process all documents
for doc_file in data_dir.glob("*.json"):
    chunks = processor.process(str(doc_file), "json")
    # Index in Weaviate, PostgreSQL, etc.
```

All models are **completely free and open** for commercial use!
