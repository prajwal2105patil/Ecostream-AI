"""
RAG Chain Builder
Member 2 (LLM/NLP Lead) — Prajwal Patil owns this file.

LLM LOCKED per CLAUDE.md R7:  Groq · llama-3.1-8b-instant · temp 0.2
Hallucination guard per R4:   similarity < 0.20 → HARDCODED_FALLBACK
"""

import os
from typing import Optional

from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_groq import ChatGroq

from rag.prompt_templates import WASTE_ADVICE_PROMPT

_chain_cache: Optional[object] = None

# R4 — Hardcoded fallback when similarity score < 0.20 (SIMILARITY_THRESHOLD)
HARDCODED_FALLBACK = (
    "I could not find specific guidelines for this waste type in my knowledge base. "
    "As a safe default under Indian SWM Rules 2016:\n"
    "• Dry waste (plastic, paper, metal, glass) → Blue Bin\n"
    "• Wet waste (food, garden) → Green Bin\n"
    "• Hazardous (batteries, medicines, e-waste) → Red Bin\n"
    "Contact your local municipal body (BBMP/MCD/MCGM) for specific instructions."
)

# Empirical gap: relevant waste queries score 0.30–0.40; out-of-domain score negative.
# 0.20 cleanly separates the two without over-filtering borderline waste terms.
SIMILARITY_THRESHOLD = 0.20


def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def _get_llm(groq_api_key: str = "") -> ChatGroq:
    """LOCKED: Groq · llama-3.1-8b-instant · temp 0.2 (CLAUDE.md R7)."""
    key = groq_api_key or os.environ.get("GROQ_API_KEY", "")
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY not set. Add it to .env — get a free key at console.groq.com/keys"
        )
    return ChatGroq(model="llama-3.1-8b-instant", temperature=0.2, api_key=key)


def build_rag_chain(persist_dir: str, groq_api_key: str = ""):
    """Build LCEL RAG chain: ChromaDB retriever → Groq LLM."""
    embeddings = get_embeddings()
    vectorstore = Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings,
        collection_name="waste_knowledge",
    )
    llm = _get_llm(groq_api_key)
    answer_chain = WASTE_ADVICE_PROMPT | llm | StrOutputParser()

    def _retrieve_and_answer(inputs: dict) -> dict:
        """
        R4 Hallucination Guard (manual score filter).

        LangChain's similarity_score_threshold is unreliable with ChromaDB —
        negative-scored docs bypass the filter. We use
        similarity_search_with_relevance_scores directly, apply SIMILARITY_THRESHOLD
        ourselves, and short-circuit BEFORE the LLM call when no docs pass.

        Empirical score ranges observed:
          Relevant waste queries   : 0.30 – 0.40
          Out-of-domain queries    : negative (< 0)
          SIMILARITY_THRESHOLD=0.20: clean separation with headroom on both sides.
        """
        query = inputs["query"]
        try:
            scored = vectorstore.similarity_search_with_relevance_scores(query, k=4)
            source_docs = [doc for doc, score in scored if score >= SIMILARITY_THRESHOLD]
        except Exception:
            source_docs = []

        # Short-circuit: no relevant docs → skip LLM entirely to prevent hallucination
        if not source_docs:
            return {"result": None, "source_documents": []}

        context = "\n\n".join(doc.page_content for doc in source_docs)
        result = answer_chain.invoke({"context": context, "question": query})
        return {"result": result, "source_documents": source_docs}

    return RunnableLambda(_retrieve_and_answer)


def get_chain(persist_dir: str, groq_api_key: str = "", **kwargs):
    """Cached singleton chain builder."""
    global _chain_cache
    if _chain_cache is None:
        _chain_cache = build_rag_chain(persist_dir, groq_api_key)
    return _chain_cache


# Layer 1 guard: all valid class names YOLO can produce.
# Any class not in this set is either a non-YOLO input or API abuse.
_VALID_WASTE_CLASSES = {
    "plastic_pet_bottle", "plastic_bag", "plastic_wrapper", "glass_bottle",
    "glass_broken", "paper_newspaper", "paper_cardboard", "metal_can",
    "metal_scrap", "organic_food_waste", "organic_leaves", "e_waste_phone",
    "e_waste_battery", "textile_cloth", "rubber_tire", "construction_debris",
    "medical_waste_mask", "thermocol", "tetra_pak", "mixed_waste",
}


def query_waste_advice(
    detected_classes: list[str],
    city: str,
    chain,
) -> tuple[str, list[str]]:
    """
    Query RAG chain. Returns (advice_text, source_chunks).

    Two-layer R4 hallucination guard:
      Layer 1 — class name whitelist: rejects non-YOLO / API-abuse input before
                any DB or LLM call.
      Layer 2 — similarity score filter in _retrieve_and_answer: rejects free-text
                chat queries (SSE path) that have no relevant knowledge base matches.
    """
    # Layer 1: drop any class names not from our 20-class YOLO model
    valid_classes = [c for c in detected_classes if c in _VALID_WASTE_CLASSES]
    if not valid_classes:
        return HARDCODED_FALLBACK, []

    query = (
        f"Disposal advice for the following waste items detected in {city}, India: "
        + ", ".join(valid_classes)
    )
    result = chain.invoke({"query": query})
    source_docs = result.get("source_documents", [])

    # Layer 2: triggers when _retrieve_and_answer found no docs above score threshold
    if not source_docs:
        return HARDCODED_FALLBACK, []

    answer = result.get("result") or HARDCODED_FALLBACK
    sources = [doc.page_content[:200] for doc in source_docs]
    return answer, sources
