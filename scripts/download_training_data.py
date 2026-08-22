#!/usr/bin/env python3
"""Download and prepare insurance/healthcare training data for RAG."""

import json
import requests
import logging
from pathlib import Path
from typing import List, Dict
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataDownloader:
    """Download open-source insurance and healthcare datasets."""

    def __init__(self, base_dir: str = "data/raw/insurance_healthcare"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Data directory: {self.base_dir}")

    def generate_healthcare_documents(self) -> int:
        """Generate realistic healthcare documents for training."""
        logger.info("\n[1/5] Generating Healthcare Documents...")

        healthcare_docs = {
            "documents": [
                {
                    "id": "health_001",
                    "title": "Understanding Health Insurance Coverage",
                    "category": "Health Insurance",
                    "content": """Health insurance is a contract between you and an insurance company that
                    helps pay for medical care. There are different types of health insurance plans including
                    HMO, PPO, EPO, and POS plans. Each plan type has different rules about which doctors and
                    hospitals you can use and how much you'll pay for care. A deductible is the amount you must
                    pay out of your own pocket before your insurance starts to pay. A copay is a fixed amount
                    you pay for a specific service. Coinsurance is a percentage of the cost you pay after meeting
                    your deductible."""
                },
                {
                    "id": "health_002",
                    "title": "Pre-existing Conditions and Coverage",
                    "category": "Health Insurance",
                    "content": """A pre-existing condition is any health problem that existed before your
                    health insurance coverage began. Under the Affordable Care Act (ACA), health insurance
                    companies cannot deny you coverage or charge you more because of a pre-existing condition.
                    This includes diabetes, heart disease, asthma, and cancer. You cannot be excluded from
                    coverage or have coverage limitations because of a pre-existing condition. Insurance
                    companies also cannot require a waiting period before covering your pre-existing condition."""
                },
                {
                    "id": "health_003",
                    "title": "How to File an Insurance Claim",
                    "category": "Claims Process",
                    "content": """To file an insurance claim: 1) Get medical services from an in-network
                    provider. 2) Your provider submits the claim to your insurance company. 3) The insurance
                    company reviews the claim for eligibility. 4) They determine how much they will pay.
                    5) You receive an Explanation of Benefits (EOB) showing what was covered. 6) You pay your
                    portion including copay, coinsurance, and deductible. 7) Your provider receives payment.
                    Most claims are processed within 3-5 business days. Out-of-network claims may take longer."""
                },
                {
                    "id": "health_004",
                    "title": "Prescription Drug Coverage and Formularies",
                    "category": "Prescription Coverage",
                    "content": """A formulary is a list of medications covered by your insurance plan.
                    Medications are typically organized into tiers. Tier 1 includes generic drugs with the
                    lowest cost. Tier 2 includes preferred brand-name drugs with moderate cost. Tier 3 includes
                    non-preferred brand-name drugs with higher cost. Tier 4 includes specialty drugs with the
                    highest cost. Some medications may require prior authorization from your doctor or may have
                    quantity limitations. You may need to try a generic version first before your insurance
                    covers the brand-name version."""
                },
                {
                    "id": "health_005",
                    "title": "In-Network vs Out-of-Network Providers",
                    "category": "Provider Network",
                    "content": """In-network providers have negotiated rates with your insurance company,
                    resulting in lower out-of-pocket costs. Out-of-network providers don't have negotiated rates
                    and your costs are typically 30-50% higher. In-network care counts toward your deductible and
                    out-of-pocket maximum. Out-of-network care may not count toward these limits. Emergency care
                    is usually covered regardless of network status. Check your insurance provider's website for
                    a list of in-network doctors and hospitals."""
                },
                {
                    "id": "health_006",
                    "title": "Understanding Deductibles and Out-of-Pocket Maximums",
                    "category": "Coverage Terms",
                    "content": """A deductible is the amount you must pay for health care services before
                    your insurance company starts to pay its share. For example, with a $1,500 deductible, you
                    pay the first $1,500 of covered services. After you meet your deductible, you usually pay
                    a copay for visits and coinsurance for other services. Your out-of-pocket maximum is the
                    most you have to pay in a year. Once you reach your out-of-pocket maximum, your insurance
                    company pays 100% of covered services for the rest of the year."""
                },
                {
                    "id": "health_007",
                    "title": "Preventive Care and Wellness Benefits",
                    "category": "Benefits",
                    "content": """Many health insurance plans cover preventive care services at no cost to you,
                    including annual wellness visits, screenings, and vaccinations. These include colonoscopies,
                    mammograms, blood pressure checks, cholesterol screenings, and flu shots. Preventive care is
                    covered before you meet your deductible. Staying up-to-date with preventive care can help
                    catch health problems early and reduce overall healthcare costs. Ask your doctor which
                    preventive services are recommended for you based on your age and health history."""
                },
                {
                    "id": "health_008",
                    "title": "Emergency Room and Urgent Care Coverage",
                    "category": "Emergency Care",
                    "content": """Emergency room care is covered for serious health conditions that require
                    immediate treatment, such as severe injuries, chest pain, or difficulty breathing. Emergency
                    care is usually covered even if you use an out-of-network facility. Urgent care centers provide
                    treatment for non-life-threatening illnesses and injuries that can't wait for a regular doctor's
                    appointment. The cost of urgent care is typically lower than emergency room care. Always contact
                    your insurance company as soon as possible after an emergency visit."""
                },
                {
                    "id": "health_009",
                    "title": "Mental Health and Behavioral Health Coverage",
                    "category": "Mental Health",
                    "content": """Most health insurance plans cover mental health services including therapy,
                    counseling, and psychiatric care. Coverage typically includes office visits, group therapy,
                    hospital stays, and prescription medications for mental health conditions. You may need a
                    referral from your primary care doctor to see a mental health specialist. Some plans have
                    limits on the number of therapy visits covered per year. Mental health coverage must be provided
                    equally with physical health coverage under parity laws."""
                },
                {
                    "id": "health_010",
                    "title": "Maternity and Newborn Care Coverage",
                    "category": "Family Planning",
                    "content": """Health insurance plans must cover maternity and newborn care services. Coverage
                    includes prenatal care, labor and delivery, hospital stay, and postpartum care. Preventive
                    services like prenatal vitamins and screening tests are covered with no copay. Newborn care
                    includes hospital stays, vaccinations, and screening tests. If you're planning to have a baby,
                    notify your insurance company and make sure your doctor is in-network. Some plans have maternity
                    waiting periods, though this is less common after the ACA."""
                }
            ]
        }

        file_path = self.base_dir / "healthcare_documents.json"
        with open(file_path, "w") as f:
            json.dump(healthcare_docs, f, indent=2)

        logger.info(f"✓ Generated {len(healthcare_docs['documents'])} healthcare documents")
        return len(healthcare_docs['documents'])

    def generate_insurance_qa(self) -> int:
        """Generate realistic insurance Q&A dataset."""
        logger.info("\n[2/5] Generating Insurance Q&A Dataset...")

        qa_pairs = {
            "qa_pairs": [
                {
                    "id": "qa_001",
                    "question": "What is health insurance?",
                    "answer": "Health insurance is a contract that helps pay for medical care and hospital stays. It protects you from high medical bills."
                },
                {
                    "id": "qa_002",
                    "question": "What is a deductible?",
                    "answer": "A deductible is the amount you must pay for health care services before your insurance starts to pay."
                },
                {
                    "id": "qa_003",
                    "question": "What is a copay?",
                    "answer": "A copay is a fixed amount you pay for a specific healthcare service, like a doctor visit or prescription."
                },
                {
                    "id": "qa_004",
                    "question": "What types of health insurance plans exist?",
                    "answer": "The main types are HMO, PPO, EPO, and POS plans. Each has different rules about which doctors you can see and how much you pay."
                },
                {
                    "id": "qa_005",
                    "question": "Can insurance deny coverage for pre-existing conditions?",
                    "answer": "No. Under the Affordable Care Act, insurance cannot deny coverage or charge more because of pre-existing conditions."
                },
                {
                    "id": "qa_006",
                    "question": "How long does a claim take to process?",
                    "answer": "Most insurance claims are processed within 3-5 business days. Out-of-network claims may take longer."
                },
                {
                    "id": "qa_007",
                    "question": "What is an out-of-pocket maximum?",
                    "answer": "It's the most you have to pay in a year. Once you reach it, your insurance covers 100% of covered services."
                },
                {
                    "id": "qa_008",
                    "question": "Is emergency care covered?",
                    "answer": "Yes, emergency care is covered even if you use an out-of-network facility for serious health conditions."
                },
                {
                    "id": "qa_009",
                    "question": "What is coinsurance?",
                    "answer": "Coinsurance is the percentage of costs you pay after meeting your deductible. For example, you might pay 20% and insurance pays 80%."
                },
                {
                    "id": "qa_010",
                    "question": "Are mental health services covered?",
                    "answer": "Yes, most plans cover mental health services including therapy, counseling, and psychiatric care equally with physical health."
                },
                {
                    "id": "qa_011",
                    "question": "How do I find in-network doctors?",
                    "answer": "Check your insurance company's website for a provider directory. You can search by specialty, location, and availability."
                },
                {
                    "id": "qa_012",
                    "question": "What is a formulary?",
                    "answer": "A formulary is a list of medications covered by your insurance plan, organized by cost tiers."
                },
                {
                    "id": "qa_013",
                    "question": "Do I need a referral to see a specialist?",
                    "answer": "It depends on your plan type. PPO plans don't require referrals, but HMO and POS plans typically do."
                },
                {
                    "id": "qa_014",
                    "question": "Are preventive services covered?",
                    "answer": "Yes, preventive services like vaccines and screenings are covered with no copay before you meet your deductible."
                },
                {
                    "id": "qa_015",
                    "question": "What is an EOB?",
                    "answer": "An Explanation of Benefits (EOB) is a statement showing what your insurance covered, what you owe, and claim details."
                }
            ]
        }

        file_path = self.base_dir / "insurance_qa.json"
        with open(file_path, "w") as f:
            json.dump(qa_pairs, f, indent=2)

        logger.info(f"✓ Generated {len(qa_pairs['qa_pairs'])} insurance Q&A pairs")
        return len(qa_pairs['qa_pairs'])

    def generate_medical_procedures(self) -> int:
        """Generate medical procedures and treatments data."""
        logger.info("\n[3/5] Generating Medical Procedures and Treatments...")

        procedures = {
            "procedures": [
                {
                    "id": "proc_001",
                    "name": "Colonoscopy",
                    "description": "A screening procedure to examine the large intestine for polyps or cancer. Recommended for adults 45 and older.",
                    "coverage": "Preventive care - covered with no copay"
                },
                {
                    "id": "proc_002",
                    "name": "Mammography",
                    "description": "Breast imaging procedure used to detect breast cancer. Recommended annually for women 40 and older.",
                    "coverage": "Preventive care - covered with no copay"
                },
                {
                    "id": "proc_003",
                    "name": "Blood Pressure Check",
                    "description": "Basic screening to measure blood pressure and detect hypertension. Covered as preventive care.",
                    "coverage": "Preventive care - covered with no copay"
                },
                {
                    "id": "proc_004",
                    "name": "Cholesterol Screening",
                    "description": "Blood test to measure cholesterol levels. Recommended for early detection of heart disease risk.",
                    "coverage": "Preventive care - covered with no copay"
                },
                {
                    "id": "proc_005",
                    "name": "Influenza Vaccination",
                    "description": "Annual flu shot to prevent influenza infection. Recommended for all individuals 6 months and older.",
                    "coverage": "Preventive care - covered with no copay"
                },
                {
                    "id": "proc_006",
                    "name": "MRI Scan",
                    "description": "Imaging procedure using magnetic fields to create detailed images of soft tissues.",
                    "coverage": "Requires deductible and coinsurance; may need prior authorization"
                },
                {
                    "id": "proc_007",
                    "name": "CT Scan",
                    "description": "Computed tomography scan using X-rays to create cross-sectional images.",
                    "coverage": "Requires deductible and coinsurance; may need prior authorization"
                },
                {
                    "id": "proc_008",
                    "name": "Physical Therapy",
                    "description": "Treatment to restore function and reduce pain after injury or surgery.",
                    "coverage": "Typically requires referral and has session limits"
                },
                {
                    "id": "proc_009",
                    "name": "Joint Replacement Surgery",
                    "description": "Surgical procedure to replace damaged joints, commonly done for knee or hip arthritis.",
                    "coverage": "Requires hospitalization costs and surgical facility fees"
                },
                {
                    "id": "proc_010",
                    "name": "Cardiac Stress Test",
                    "description": "Test to evaluate heart function during exercise. Used to diagnose heart conditions.",
                    "coverage": "Requires deductible and coinsurance; may need prior authorization"
                }
            ]
        }

        file_path = self.base_dir / "medical_procedures.json"
        with open(file_path, "w") as f:
            json.dump(procedures, f, indent=2)

        logger.info(f"✓ Generated {len(procedures['procedures'])} medical procedures")
        return len(procedures['procedures'])

    def generate_drug_information(self) -> int:
        """Generate common FDA-approved drug information."""
        logger.info("\n[4/5] Generating Drug Information...")

        drugs = {
            "drugs": [
                {
                    "id": "drug_001",
                    "name": "Lisinopril",
                    "class": "ACE Inhibitor",
                    "use": "Treatment of high blood pressure and heart failure",
                    "side_effects": "Dizziness, cough, hyperkalemia",
                    "contraindications": "Pregnancy, angioedema, severe kidney disease",
                    "fda_approval": "Approved for hypertension and heart failure"
                },
                {
                    "id": "drug_002",
                    "name": "Metformin",
                    "class": "Biguanide",
                    "use": "Treatment of type 2 diabetes mellitus",
                    "side_effects": "Gastrointestinal upset, metallic taste, vitamin B12 deficiency",
                    "contraindications": "Severe kidney disease, metabolic acidosis",
                    "fda_approval": "First-line treatment for type 2 diabetes"
                },
                {
                    "id": "drug_003",
                    "name": "Atorvastatin",
                    "class": "Statin",
                    "use": "Reduction of cholesterol and prevention of heart disease",
                    "side_effects": "Muscle pain, liver problems, memory issues",
                    "contraindications": "Active liver disease, pregnancy",
                    "fda_approval": "Approved for hypercholesterolemia and cardiovascular disease"
                },
                {
                    "id": "drug_004",
                    "name": "Sertraline",
                    "class": "SSRI",
                    "use": "Treatment of depression, anxiety, and PTSD",
                    "side_effects": "Sexual dysfunction, insomnia, weight changes",
                    "contraindications": "MAOI use, bipolar disorder, angle-closure glaucoma",
                    "fda_approval": "Approved for depression, panic disorder, PTSD, OCD"
                },
                {
                    "id": "drug_005",
                    "name": "Omeprazole",
                    "class": "Proton Pump Inhibitor",
                    "use": "Reduction of stomach acid for GERD and ulcers",
                    "side_effects": "Headache, B12 deficiency, fractures with long-term use",
                    "contraindications": "Long-term use with certain medications",
                    "fda_approval": "Approved for GERD and peptic ulcer disease"
                }
            ]
        }

        file_path = self.base_dir / "drug_information.json"
        with open(file_path, "w") as f:
            json.dump(drugs, f, indent=2)

        logger.info(f"✓ Generated {len(drugs['drugs'])} drug information entries")
        return len(drugs['drugs'])

    def download_all(self):
        """Download/generate all datasets."""
        logger.info("Starting data preparation for Insurance/Healthcare RAG...")
        logger.info("(Generating sample datasets for demonstration)\n")

    def create_summary_report(self):
        """Create summary report of downloaded data."""
        logger.info("\n" + "="*60)
        logger.info("DATA PREPARATION SUMMARY")
        logger.info("="*60)

        total_size = 0
        file_count = 0

        for file_path in self.base_dir.rglob("*"):
            if file_path.is_file():
                size_mb = file_path.stat().st_size / (1024 * 1024)
                total_size += size_mb
                file_count += 1
                logger.info(f"  {file_path.name}: {size_mb:.2f} MB")

        logger.info("="*60)
        logger.info(f"Total files: {file_count}")
        logger.info(f"Total size: {total_size:.2f} MB")
        logger.info(f"Location: {self.base_dir}")
        logger.info("="*60)

        # Next steps
        logger.info("\nNEXT STEPS:")
        logger.info("1. Process data into chunks for RAG:")
        logger.info("   python scripts/chunk_and_prepare_data.py")
        logger.info("")
        logger.info("2. Index documents in Weaviate:")
        logger.info("   python scripts/index_documents.py")
        logger.info("")
        logger.info("3. Start the RAG system:")
        logger.info("   python -m uvicorn src.main:app --reload")
        logger.info("")
        logger.info("4. Test with a query:")
        logger.info("   curl -X POST http://localhost:8000/api/v1/default-tenant/query \\")
        logger.info('     -d \'{"query": "What is health insurance?"}\'')
        logger.info("")

    def download_all(self):
        """Generate all sample datasets."""
        logger.info("Starting data preparation for Insurance/Healthcare RAG...")
        logger.info("(Generating comprehensive sample datasets)\n")

        results = {
            "Healthcare Documents": self.generate_healthcare_documents(),
            "Insurance Q&A": self.generate_insurance_qa(),
            "Medical Procedures": self.generate_medical_procedures(),
            "Drug Information": self.generate_drug_information(),
        }

        self.create_summary_report()

        return results


if __name__ == "__main__":
    downloader = DataDownloader()
    results = downloader.download_all()

    logger.info("\n✓ Data preparation completed!")
    logger.info("\nGenerated training data for:")
    logger.info(f"  • Healthcare Documents: {results['Healthcare Documents']} documents")
    logger.info(f"  • Insurance Q&A: {results['Insurance Q&A']} Q&A pairs")
    logger.info(f"  • Medical Procedures: {results['Medical Procedures']} procedures")
    logger.info(f"  • Drug Information: {results['Drug Information']} drugs")
    logger.info(f"\nTotal: {sum(results.values())} documents ready for RAG training")
    logger.info("\nThese are comprehensive sample datasets for testing your RAG system.")
    logger.info("For production, add your own domain-specific documents to: " + str(downloader.base_dir))
    logger.info("\nNext: Run chunk_and_prepare_data.py to process this data")
