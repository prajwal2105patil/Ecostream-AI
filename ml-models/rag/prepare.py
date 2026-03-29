"""
RAG Data Preparation — EcoStream AI Autoresearch
STATIC FILE: The autoresearch agent must NEVER modify this file.

Orchestrates the RAG data pipeline:
  1. Build the production ChromaDB vectorstore from knowledge_base/ documents
  2. Verify test queries exist at data/rag_eval/test_queries.json
  3. Print summary statistics

Usage:
    python ml-models/rag/prepare.py
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Add ml-models/rag to sys.path for sibling imports
_rag_dir = str(PROJECT_ROOT / "ml-models" / "rag")
if _rag_dir not in sys.path:
    sys.path.insert(0, _rag_dir)

KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "data" / "knowledge_base"
CHROMA_PERSIST_DIR = PROJECT_ROOT / "data" / "chroma_db"
TEST_QUERIES_PATH = PROJECT_ROOT / "data" / "rag_eval" / "test_queries.json"


def build_production_vectorstore():
    """Build the production vectorstore using the canonical build_vectorstore module."""
    import os
    # Temporarily change to project root so build_vectorstore resolves paths correctly
    old_cwd = os.getcwd()
    os.chdir(str(PROJECT_ROOT))
    try:
        from build_vectorstore import build_vectorstore
        build_vectorstore()
    finally:
        os.chdir(old_cwd)


def verify_knowledge_base():
    """Check that knowledge base documents exist and print stats."""
    if not KNOWLEDGE_BASE_DIR.exists():
        print(f"[ERROR] Knowledge base not found: {KNOWLEDGE_BASE_DIR}")
        return False

    docs = list(KNOWLEDGE_BASE_DIR.rglob("*.txt")) + list(KNOWLEDGE_BASE_DIR.rglob("*.pdf"))
    if not docs:
        print("[ERROR] No .txt or .pdf files in knowledge_base/")
        return False

    total_bytes = sum(f.stat().st_size for f in docs)
    print(f"  Found {len(docs)} documents ({total_bytes / 1024:.1f} KB)")
    for doc in sorted(docs):
        rel = doc.relative_to(KNOWLEDGE_BASE_DIR)
        print(f"    {rel} ({doc.stat().st_size / 1024:.1f} KB)")
    return True


def verify_test_queries():
    """Check that test queries JSON exists and print summary."""
    if not TEST_QUERIES_PATH.exists():
        print(f"[ERROR] Test queries not found: {TEST_QUERIES_PATH}")
        print("  Create data/rag_eval/test_queries.json with gold-standard queries.")
        return False

    queries = json.loads(TEST_QUERIES_PATH.read_text(encoding="utf-8"))
    tiers = {}
    for q in queries:
        tier = q.get("relevance_tier", "unknown")
        tiers[tier] = tiers.get(tier, 0) + 1

    print(f"  Test queries: {len(queries)} total")
    for tier, count in sorted(tiers.items()):
        print(f"    {tier}: {count}")
    return True


def main():
    print("=" * 60)
    print("  EcoStream AI — RAG Data Preparation")
    print("=" * 60)

    print("\n[Step 1/3] Verifying knowledge base...")
    if not verify_knowledge_base():
        sys.exit(1)

    print("\n[Step 2/3] Building production vectorstore...")
    build_production_vectorstore()

    print("\n[Step 3/3] Verifying test queries...")
    if not verify_test_queries():
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  RAG preparation complete!")
    print(f"  Vectorstore: {CHROMA_PERSIST_DIR}")
    print(f"  Test queries: {TEST_QUERIES_PATH}")
    print("  Next: python ml-models/rag/train.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
