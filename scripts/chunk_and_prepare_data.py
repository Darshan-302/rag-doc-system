#!/usr/bin/env python3
"""Chunk and prepare training data for RAG system."""

import json
import logging
from pathlib import Path
from typing import List, Dict
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataPreprocessor:
    """Preprocess raw data into RAG-ready chunks."""

    def __init__(
        self,
        raw_dir: str = "data/raw/insurance_healthcare",
        output_dir: str = "data/processed"
    ):
        self.raw_dir = Path(raw_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove special characters but keep medical terms
        text = re.sub(r'[\r\n\t]', ' ', text)

        # Normalize common abbreviations
        replacements = {
            r'\bDr\.': 'Doctor',
            r'\bRx\b': 'Prescription',
            r'\bDx\b': 'Diagnosis',
            r'\bTx\b': 'Treatment',
            r'\bN/A': 'Not Available',
        }

        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)

        return text.strip()

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 512,
        overlap: int = 50
    ) -> List[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Input text
            chunk_size: Target chunk size in words
            overlap: Overlap between chunks in words

        Returns:
            List of text chunks
        """
        # Split into words
        words = text.split()

        if len(words) <= chunk_size:
            return [text] if text.strip() else []

        chunks = []

        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            chunk = ' '.join(chunk_words)

            if chunk.strip():
                chunks.append(chunk)

        return chunks

    def process_fda_drugs(self) -> int:
        """Process FDA drug data."""
        logger.info("Processing FDA drug data...")

        file_path = self.raw_dir / "fda_drugs.txt"
        if not file_path.exists():
            logger.warning(f"  FDA drugs file not found: {file_path}")
            return 0

        chunks_data = []

        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # Simple parsing of FDA format
            drugs = content.split('\n\n')

            for drug_idx, drug_text in enumerate(drugs):
                if not drug_text.strip():
                    continue

                # Clean text
                cleaned = self.clean_text(drug_text)

                # Chunk the drug info
                chunks = self.chunk_text(cleaned, chunk_size=256, overlap=20)

                for chunk_idx, chunk in enumerate(chunks):
                    chunks_data.append({
                        "document_id": f"fda_drug_{drug_idx}",
                        "chunk_id": chunk_idx,
                        "text": chunk,
                        "source": "FDA Orange Book",
                        "source_type": "Drug Information",
                        "metadata": {
                            "data_type": "FDA Drug"
                        }
                    })

            logger.info(f"  ✓ Processed {len(drugs)} drugs → {len(chunks_data)} chunks")
            return len(chunks_data)

        except Exception as e:
            logger.error(f"  ✗ Error processing FDA drugs: {e}")
            return 0

    def process_insurance_qa(self) -> int:
        """Process InsuranceQA dataset."""
        logger.info("Processing InsuranceQA data...")

        qa_dir = self.raw_dir / "insurance_qa"
        if not qa_dir.exists():
            logger.warning(f"  InsuranceQA directory not found: {qa_dir}")
            return 0

        chunks_data = []
        doc_count = 0

        try:
            # Process corpus files
            for corpus_file in qa_dir.glob("corpus_*.txt"):
                with open(corpus_file, 'r') as f:
                    lines = f.readlines()

                for line_idx, line in enumerate(lines):
                    if not line.strip():
                        continue

                    # Clean and chunk
                    cleaned = self.clean_text(line)
                    chunks = self.chunk_text(cleaned, chunk_size=256, overlap=20)

                    for chunk_idx, chunk in enumerate(chunks):
                        chunks_data.append({
                            "document_id": f"insurance_qa_{corpus_file.stem}_{line_idx}",
                            "chunk_id": chunk_idx,
                            "text": chunk,
                            "source": "InsuranceQA",
                            "source_type": "Q&A",
                            "metadata": {
                                "file": corpus_file.name,
                                "line_number": line_idx
                            }
                        })
                    doc_count += 1

            logger.info(f"  ✓ Processed {doc_count} Q&A entries → {len(chunks_data)} chunks")
            return len(chunks_data)

        except Exception as e:
            logger.error(f"  ✗ Error processing InsuranceQA: {e}")
            return 0

    def process_clinical_trials(self) -> int:
        """Process clinical trials data."""
        logger.info("Processing clinical trials data...")

        file_path = self.raw_dir / "clinical_trials.json"
        if not file_path.exists():
            logger.warning(f"  Clinical trials file not found: {file_path}")
            return 0

        chunks_data = []

        try:
            with open(file_path, 'r') as f:
                trials = json.load(f)

            for trial_idx, trial in enumerate(trials):
                # Create document text from trial info
                text_parts = []

                if trial.get("title"):
                    text_parts.append(f"Title: {trial['title']}")

                if trial.get("condition"):
                    conditions = trial['condition'] if isinstance(trial['condition'], list) else [trial['condition']]
                    text_parts.append(f"Conditions: {', '.join(filter(None, conditions))}")

                if trial.get("phase"):
                    phases = trial['phase'] if isinstance(trial['phase'], list) else [trial['phase']]
                    text_parts.append(f"Phase: {', '.join(filter(None, phases))}")

                if trial.get("status"):
                    text_parts.append(f"Status: {trial['status']}")

                if not text_parts:
                    continue

                trial_text = ' '.join(text_parts)

                # Clean and chunk
                cleaned = self.clean_text(trial_text)
                chunks = self.chunk_text(cleaned, chunk_size=256, overlap=20)

                for chunk_idx, chunk in enumerate(chunks):
                    chunks_data.append({
                        "document_id": f"trial_{trial_idx}",
                        "chunk_id": chunk_idx,
                        "text": chunk,
                        "source": "Clinical Trials",
                        "source_type": "Medical Research",
                        "metadata": {
                            "condition": trial.get("condition"),
                            "phase": trial.get("phase"),
                            "status": trial.get("status")
                        }
                    })

            logger.info(f"  ✓ Processed {len(trials)} trials → {len(chunks_data)} chunks")
            return len(chunks_data)

        except Exception as e:
            logger.error(f"  ✗ Error processing clinical trials: {e}")
            return 0

    def process_sample_policies(self) -> int:
        """Process sample insurance policies."""
        logger.info("Processing sample insurance policies...")

        file_path = self.raw_dir / "sample_insurance_policies.json"
        if not file_path.exists():
            logger.warning(f"  Sample policies file not found: {file_path}")
            return 0

        chunks_data = []

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            policies = data.get("policies", [])

            for policy in policies:
                content = f"{policy.get('name', '')}. {policy.get('content', '')}"

                # Clean and chunk
                cleaned = self.clean_text(content)
                chunks = self.chunk_text(cleaned, chunk_size=256, overlap=20)

                for chunk_idx, chunk in enumerate(chunks):
                    chunks_data.append({
                        "document_id": policy.get("id"),
                        "chunk_id": chunk_idx,
                        "text": chunk,
                        "source": "Insurance Policies",
                        "source_type": "Policy",
                        "metadata": {
                            "policy_name": policy.get("name"),
                            "category": policy.get("category")
                        }
                    })

            logger.info(f"  ✓ Processed {len(policies)} policies → {len(chunks_data)} chunks")
            return len(chunks_data)

        except Exception as e:
            logger.error(f"  ✗ Error processing sample policies: {e}")
            return 0

    def save_chunks(self, all_chunks: List[Dict], output_file: str = "rag_training_data.jsonl"):
        """Save chunks to JSONL format (one chunk per line)."""
        output_path = self.output_dir / output_file

        with open(output_path, 'w') as f:
            for chunk in all_chunks:
                f.write(json.dumps(chunk) + '\n')

        logger.info(f"\n✓ Saved {len(all_chunks)} chunks to {output_path}")
        return output_path

    def generate_statistics(self, chunks: List[Dict]):
        """Generate and log statistics about chunks."""
        logger.info("\n" + "="*60)
        logger.info("CHUNK STATISTICS")
        logger.info("="*60)

        total_chunks = len(chunks)
        total_chars = sum(len(c.get('text', '')) for c in chunks)
        avg_chars = total_chars / total_chunks if total_chunks > 0 else 0

        # Count by source
        sources = {}
        for chunk in chunks:
            source = chunk.get('source', 'Unknown')
            sources[source] = sources.get(source, 0) + 1

        logger.info(f"Total chunks: {total_chunks}")
        logger.info(f"Total characters: {total_chars:,}")
        logger.info(f"Average chunk size: {avg_chars:.0f} characters")
        logger.info(f"\nChunks by source:")

        for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_chunks) * 100
            logger.info(f"  {source}: {count} ({percentage:.1f}%)")

        logger.info("="*60)

    def process_all(self):
        """Process all datasets."""
        logger.info("Starting data preprocessing...\n")

        all_chunks = []

        # Process each data source
        all_chunks.extend(self._load_processed_chunks(self.process_fda_drugs()))
        all_chunks.extend(self._load_processed_chunks(self.process_insurance_qa()))
        all_chunks.extend(self._load_processed_chunks(self.process_clinical_trials()))
        all_chunks.extend(self._load_processed_chunks(self.process_sample_policies()))

        # Actually, let's reprocess with actual data collection
        logger.info("\nProcessing all data sources...")

        chunks_fda = []
        chunks_qa = []
        chunks_trials = []
        chunks_policies = []

        # FDA Drugs
        try:
            file_path = self.raw_dir / "fda_drugs.txt"
            if file_path.exists():
                with open(file_path, 'r') as f:
                    content = f.read()
                for i, drug_section in enumerate(content.split('\n\n')[:100]):  # Limit for demo
                    if drug_section.strip():
                        chunks = self.chunk_text(self.clean_text(drug_section))
                        for j, chunk in enumerate(chunks):
                            chunks_fda.append({
                                "document_id": f"fda_{i}",
                                "chunk_id": j,
                                "text": chunk,
                                "source": "FDA Orange Book",
                                "source_type": "Drug Information"
                            })
        except Exception as e:
            logger.warning(f"Could not process FDA drugs: {e}")

        # InsuranceQA
        try:
            qa_dir = self.raw_dir / "insurance_qa"
            if qa_dir.exists():
                for corpus_file in list(qa_dir.glob("corpus_*.txt"))[:5]:
                    with open(corpus_file, 'r') as f:
                        for line_idx, line in enumerate(f.readlines()[:100]):
                            if line.strip():
                                chunks = self.chunk_text(self.clean_text(line))
                                for j, chunk in enumerate(chunks):
                                    chunks_qa.append({
                                        "document_id": f"qa_{corpus_file.stem}_{line_idx}",
                                        "chunk_id": j,
                                        "text": chunk,
                                        "source": "InsuranceQA",
                                        "source_type": "Q&A"
                                    })
        except Exception as e:
            logger.warning(f"Could not process InsuranceQA: {e}")

        # Clinical Trials
        try:
            trials_file = self.raw_dir / "clinical_trials.json"
            if trials_file.exists():
                with open(trials_file, 'r') as f:
                    trials = json.load(f)
                for i, trial in enumerate(trials[:100]):
                    trial_text = f"{trial.get('title', '')}. Conditions: {trial.get('condition', '')}. Status: {trial.get('status', '')}"
                    chunks = self.chunk_text(self.clean_text(trial_text))
                    for j, chunk in enumerate(chunks):
                        chunks_trials.append({
                            "document_id": f"trial_{i}",
                            "chunk_id": j,
                            "text": chunk,
                            "source": "Clinical Trials",
                            "source_type": "Medical Research"
                        })
        except Exception as e:
            logger.warning(f"Could not process clinical trials: {e}")

        # Sample Policies
        try:
            policies_file = self.raw_dir / "sample_insurance_policies.json"
            if policies_file.exists():
                with open(policies_file, 'r') as f:
                    data = json.load(f)
                for i, policy in enumerate(data.get('policies', [])):
                    policy_text = f"{policy.get('name', '')}. {policy.get('content', '')}"
                    chunks = self.chunk_text(self.clean_text(policy_text))
                    for j, chunk in enumerate(chunks):
                        chunks_policies.append({
                            "document_id": f"policy_{policy.get('id')}",
                            "chunk_id": j,
                            "text": chunk,
                            "source": "Insurance Policies",
                            "source_type": "Policy"
                        })
        except Exception as e:
            logger.warning(f"Could not process sample policies: {e}")

        # Combine all chunks
        all_chunks = chunks_fda + chunks_qa + chunks_trials + chunks_policies

        if not all_chunks:
            logger.warning("No chunks were generated. Check that data files exist in: " + str(self.raw_dir))
            return

        # Save chunks
        output_path = self.save_chunks(all_chunks)

        # Generate statistics
        self.generate_statistics(all_chunks)

        # Next steps
        logger.info("\nNEXT STEPS:")
        logger.info("1. Index chunks in Weaviate:")
        logger.info("   python scripts/index_documents.py")
        logger.info("")
        logger.info("2. Test RAG system:")
        logger.info("   python -m uvicorn src.main:app --reload")
        logger.info("")
        logger.info("3. Query the RAG:")
        logger.info("   curl -X POST http://localhost:8000/api/v1/default/query \\")
        logger.info("        -d '{\"query\": \"What is health insurance?\"}'")

    def _load_processed_chunks(self, count):
        """Helper to return empty list."""
        return []


if __name__ == "__main__":
    preprocessor = DataPreprocessor()
    preprocessor.process_all()

    logger.info("\n✓ Data preprocessing completed!")
