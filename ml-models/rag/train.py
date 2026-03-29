"""
EcoStream AI -- RAG Autoresearch Evaluation Harness
===========================================================================

Agent contract:
  - This is the ONLY file the autoresearch agent may edit.
  - Run: python ml-models/rag/train.py
  - Budget: 5-minute wall-clock maximum.
  - Output: Final line of stdout is a JSON metrics dict.
  - Prerequisites: Run prepare.py first to build vectorstore + verify test queries.

The agent experiments by modifying the EXPERIMENT KNOBS section below.
Everything below the FIXED CONSTANTS section must not be changed.
"""

import json
import os
import shutil
import time
from pathlib import Path

# ==========================================================================
# EXPERIMENT KNOBS -- The autoresearch agent modifies ONLY these constants
# ==========================================================================

# Chunking strategy
CHUNK_SIZE    = 500                    # Characters per chunk: 200 | 300 | 500 | 800 | 1000
CHUNK_OVERLAP = 50                     # Overlap: 0 | 25 | 50 | 100 | 150

# Embedding model
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
# Alternatives: all-mpnet-base-v2, paraphrase-MiniLM-L6-v2, multi-qa-MiniLM-L6-cos-v1

# Retrieval parameters
RETRIEVAL_K          = 4               # Top-k documents: 2 | 3 | 4 | 6 | 8
SIMILARITY_THRESHOLD = 0.20           # Score cutoff: 0.10 | 0.15 | 0.20 | 0.25 | 0.30
USE_MMR              = False           # True = MMR diversity search, False = plain similarity
MMR_LAMBDA           = 0.5            # Diversity vs relevance tradeoff (only if USE_MMR)

# Prompt template -- agent can rewrite entirely
PROMPT_TEMPLATE = """You are EcoStream AI, an expert waste management advisor for Indian cities.
Use ONLY the provided context from official Indian municipal waste regulations and recycling guidelines
to answer the question. Do not guess or invent information not in the context.

Context from Indian Municipal Guidelines:
{context}

Question (Detected waste types and user location):
{question}

Provide a structured response with:
1. **Segregation Bin**: Which bin to use (Green/Wet, Blue/Dry, Red/Hazardous)
2. **Disposal Steps**: Step-by-step instructions specific to India
3. **Nearest Facility Type**: MRF (Material Recovery Facility), Biogas Plant, TSDF (Treatment Storage Disposal Facility), or Dry Waste Collection Centre
4. **SWM Rules 2016**: Mention any relevant penalty or compliance requirement
5. **Tip**: One practical tip for Indian households handling this waste

Keep the response under 200 words. Use simple, clear English understandable by a general Indian citizen."""


# ==========================================================================
# FIXED CONSTANTS -- Agent must NOT change anything below this line
# ==========================================================================

WALL_CLOCK_BUDGET_SEC = 300            # 5 minutes -- non-negotiable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "data" / "knowledge_base"
TEST_QUERIES_PATH  = PROJECT_ROOT / "data" / "rag_eval" / "test_queries.json"
CHROMA_EXPERIMENT_DIR = PROJECT_ROOT / "data" / "chroma_experiment"

# Composite score weights
W_SOURCE_HIT   = 0.30
W_KEYWORD_RECALL = 0.30
W_GUARD_ACC    = 0.20
W_KEYWORD_PREC = 0.20

# The hardcoded fallback from rag_chain.py -- used to detect guard activation
FALLBACK_MARKER = "I could not find specific guidelines"


def _build_experiment_vectorstore():
    """Rebuild ChromaDB with current CHUNK_SIZE/OVERLAP/EMBEDDING for this experiment."""
    from langchain_community.document_loaders import TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_chroma import Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings

    # Clean slate -- avoid stale vectors from previous chunk configs
    if CHROMA_EXPERIMENT_DIR.exists():
        shutil.rmtree(CHROMA_EXPERIMENT_DIR)

    # Load documents
    docs = []
    for filepath in KNOWLEDGE_BASE_DIR.rglob("*"):
        if filepath.suffix == ".txt":
            loader = TextLoader(str(filepath), encoding="utf-8")
            docs.extend(loader.load())

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
    )
    chunks = splitter.split_documents(docs)
    print(f"  Chunked {len(docs)} docs -> {len(chunks)} chunks "
          f"(size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_EXPERIMENT_DIR),
        collection_name="waste_experiment",
    )
    print(f"  Vectorstore: {vectorstore._collection.count()} vectors in {CHROMA_EXPERIMENT_DIR}")
    return vectorstore, embeddings


def _evaluate_retrieval(vectorstore, query: str, expected: dict):
    """Run retrieval and compute per-query metrics (no LLM)."""
    if USE_MMR:
        docs = vectorstore.max_marginal_relevance_search(
            query, k=RETRIEVAL_K, lambda_mult=MMR_LAMBDA
        )
        scores = []
        for doc in docs:
            # MMR doesn't return scores directly; compute approximate score
            try:
                scored = vectorstore.similarity_search_with_relevance_scores(
                    doc.page_content[:100], k=1
                )
                scores.append(scored[0][1] if scored else 0.0)
            except Exception:
                scores.append(0.0)
        source_docs = [doc for doc, s in zip(docs, scores) if s >= SIMILARITY_THRESHOLD]
        relevance_scores = [s for s in scores if s >= SIMILARITY_THRESHOLD]
    else:
        try:
            scored = vectorstore.similarity_search_with_relevance_scores(
                query, k=RETRIEVAL_K
            )
            source_docs = [doc for doc, s in scored if s >= SIMILARITY_THRESHOLD]
            relevance_scores = [s for _, s in scored if s >= SIMILARITY_THRESHOLD]
        except Exception:
            source_docs = []
            relevance_scores = []

    # Source hit rate: did we retrieve at least one expected source doc?
    expected_sources = expected.get("expected_source_docs", [])
    source_hit = 0.0
    if expected_sources and source_docs:
        retrieved_sources = set()
        for doc in source_docs:
            src = doc.metadata.get("source", "")
            # Extract just the filename
            retrieved_sources.add(Path(src).name)
        source_hit = 1.0 if any(s in retrieved_sources for s in expected_sources) else 0.0
    elif not expected_sources:
        source_hit = 1.0  # out-of-domain: not expecting sources

    # Keyword precision: fraction of expected keywords found in retrieved context
    expected_kw = expected.get("expected_keywords", [])
    kw_precision = 0.0
    if expected_kw and source_docs:
        context = " ".join(doc.page_content.lower() for doc in source_docs)
        hits = sum(1 for kw in expected_kw if kw.lower() in context)
        kw_precision = hits / len(expected_kw)
    elif not expected_kw:
        kw_precision = 1.0  # out-of-domain: no keywords expected

    avg_score = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0

    return {
        "source_hit": source_hit,
        "keyword_precision": kw_precision,
        "avg_relevance": avg_score,
        "n_docs_retrieved": len(source_docs),
        "source_docs": source_docs,
    }


_llm_chain_cache = None


def _get_llm_chain():
    """Singleton LLM chain -- instantiated once, reused across all 18 queries."""
    global _llm_chain_cache
    if _llm_chain_cache is None:
        from langchain_groq import ChatGroq
        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        groq_key = os.environ.get("GROQ_API_KEY", "")
        if not groq_key:
            return None
        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.2, api_key=groq_key)
        prompt = PromptTemplate(
            template=PROMPT_TEMPLATE,
            input_variables=["context", "question"],
        )
        _llm_chain_cache = prompt | llm | StrOutputParser()
    return _llm_chain_cache


def _evaluate_answer(vectorstore, query: str, source_docs: list, expected: dict):
    """Call LLM and measure answer quality. Returns None if no API key."""
    chain = _get_llm_chain()
    if chain is None:
        return None

    tier = expected.get("relevance_tier", "high")

    # For out-of-domain: should NOT produce an answer (guard should have blocked)
    if tier == "out_of_domain":
        if not source_docs:
            return {"keyword_recall": 1.0, "guard_correct": 1.0, "answer_length": 0}
        # Guard failed -- LLM got called for out-of-domain query
        context = "\n\n".join(doc.page_content for doc in source_docs)
        answer = chain.invoke({"context": context, "question": query})
        return {"keyword_recall": 0.0, "guard_correct": 0.0, "answer_length": len(answer.split())}

    # In-domain: measure keyword recall and answer length
    if not source_docs:
        return {"keyword_recall": 0.0, "guard_correct": 1.0, "answer_length": 0}

    context = "\n\n".join(doc.page_content for doc in source_docs)
    answer = chain.invoke({"context": context, "question": query})

    expected_kw = expected.get("expected_keywords", [])
    kw_recall = 0.0
    if expected_kw:
        hits = sum(1 for kw in expected_kw if kw.lower() in answer.lower())
        kw_recall = hits / len(expected_kw)

    return {
        "keyword_recall": kw_recall,
        "guard_correct": 1.0,
        "answer_length": len(answer.split()),
    }


def main():
    import sys

    start = time.monotonic()

    # -- Pre-flight checks ------------------------------------------------
    if not TEST_QUERIES_PATH.exists():
        print(f"[ERROR] {TEST_QUERIES_PATH} not found. Run prepare.py first.")
        sys.exit(1)

    if not KNOWLEDGE_BASE_DIR.exists():
        print(f"[ERROR] {KNOWLEDGE_BASE_DIR} not found.")
        sys.exit(1)

    print("=" * 60)
    print("  EcoStream AI -- RAG Autoresearch Evaluation")
    print("=" * 60)
    print(f"  Chunk      : {CHUNK_SIZE} / {CHUNK_OVERLAP}")
    print(f"  Embedding  : {EMBEDDING_MODEL}")
    print(f"  K          : {RETRIEVAL_K}")
    print(f"  Threshold  : {SIMILARITY_THRESHOLD}")
    print(f"  MMR        : {USE_MMR} (lambda={MMR_LAMBDA})")
    print(f"  Budget     : {WALL_CLOCK_BUDGET_SEC}s")
    print("=" * 60)

    # -- Build experimental vectorstore -----------------------------------
    print("\n[1/3] Building experimental vectorstore...")
    vectorstore, embeddings = _build_experiment_vectorstore()

    # -- Load test queries ------------------------------------------------
    print("\n[2/3] Loading test queries...")
    queries = json.loads(TEST_QUERIES_PATH.read_text(encoding="utf-8"))
    print(f"  {len(queries)} queries loaded")

    # -- Evaluate ---------------------------------------------------------
    print("\n[3/3] Evaluating...")
    retrieval_results = []
    answer_results = []
    evaluated = 0

    has_llm = bool(os.environ.get("GROQ_API_KEY", ""))
    if not has_llm:
        print("  [WARN] GROQ_API_KEY not set -- skipping LLM answer metrics")

    for i, q in enumerate(queries):
        elapsed = time.monotonic() - start
        if elapsed > WALL_CLOCK_BUDGET_SEC - 30:  # 30s safety margin
            print(f"\n  [BUDGET] Stopping at query {i}/{len(queries)} -- {elapsed:.0f}s elapsed")
            break

        query_text = q["query"]
        tier = q.get("relevance_tier", "high")

        # Retrieval evaluation
        ret = _evaluate_retrieval(vectorstore, query_text, q)
        retrieval_results.append(ret)

        # Answer evaluation (only if LLM available)
        if has_llm:
            ans = _evaluate_answer(vectorstore, query_text, ret["source_docs"], q)
            if ans:
                answer_results.append(ans)

        evaluated += 1
        status = "HIT" if ret["source_hit"] > 0 else "MISS"
        print(f"  [{i+1:2d}/{len(queries)}] [{tier:<12}] {status} "
              f"(docs={ret['n_docs_retrieved']}, rel={ret['avg_relevance']:.3f}) "
              f"| {query_text[:50]}...")

    elapsed = time.monotonic() - start

    # -- Aggregate metrics ------------------------------------------------
    n = len(retrieval_results)
    source_hit_rate = sum(r["source_hit"] for r in retrieval_results) / n if n else 0
    keyword_precision = sum(r["keyword_precision"] for r in retrieval_results) / n if n else 0
    avg_relevance = sum(r["avg_relevance"] for r in retrieval_results) / n if n else 0

    keyword_recall = 0.0
    guard_accuracy = 0.0
    avg_answer_len = 0

    if answer_results:
        na = len(answer_results)
        keyword_recall = sum(a["keyword_recall"] for a in answer_results) / na
        guard_accuracy = sum(a["guard_correct"] for a in answer_results) / na
        avg_answer_len = int(sum(a["answer_length"] for a in answer_results) / na)

    composite = (
        W_SOURCE_HIT * source_hit_rate
        + W_KEYWORD_RECALL * keyword_recall
        + W_GUARD_ACC * guard_accuracy
        + W_KEYWORD_PREC * keyword_precision
    )

    print(f"\n{'=' * 60}")
    print(f"  Retrieval  : source_hit={source_hit_rate:.3f}  kw_prec={keyword_precision:.3f}  avg_rel={avg_relevance:.3f}")
    if answer_results:
        print(f"  Answers    : kw_recall={keyword_recall:.3f}  guard_acc={guard_accuracy:.3f}  avg_len={avg_answer_len}")
    print(f"  Composite  : {composite:.4f}")
    print(f"  Wall clock : {elapsed:.1f}s")
    print(f"{'=' * 60}")

    # -- JSON output -- MUST be the final line -----------------------------
    output = {
        "experiment": "rag",
        "wall_clock_sec": round(elapsed, 1),
        "queries_evaluated": evaluated,
        "source_hit_rate": round(source_hit_rate, 4),
        "keyword_precision": round(keyword_precision, 4),
        "keyword_recall": round(keyword_recall, 4),
        "avg_relevance_score": round(avg_relevance, 4),
        "hallucination_guard_accuracy": round(guard_accuracy, 4),
        "avg_answer_length": avg_answer_len,
        "composite_score": round(composite, 4),
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "embedding_model": EMBEDDING_MODEL,
        "retrieval_k": RETRIEVAL_K,
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "use_mmr": USE_MMR,
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
