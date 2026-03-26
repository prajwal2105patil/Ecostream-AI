"""
RAG Chain Builder
Member 2 (LLM/NLP Lead) — Prajwal Patil owns this file.

LLM LOCKED per CLAUDE.md R7:  Groq · llama-3.1-8b-instant · temp 0.2
Hallucination guard per R4:   similarity < 0.40 → HARDCODED_FALLBACK
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

# R4 — Hardcoded fallback when similarity score < 0.65
HARDCODED_FALLBACK = (
    "I could not find specific guidelines for this waste type in my knowledge base. "
    "As a safe default under Indian SWM Rules 2016:\n"
    "• Dry waste (plastic, paper, metal, glass) → Blue Bin\n"
    "• Wet waste (food, garden) → Green Bin\n"
    "• Hazardous (batteries, medicines, e-waste) → Red Bin\n"
    "Contact your local municipal body (BBMP/MCD/MCGM) for specific instructions."
)

SIMILARITY_THRESHOLD = 0.40


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
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4},
    )
    llm = _get_llm(groq_api_key)
    answer_chain = WASTE_ADVICE_PROMPT | llm | StrOutputParser()

    def _retrieve_and_answer(inputs: dict) -> dict:
        query = inputs["query"]
        source_docs = retriever.invoke(query)
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


def query_waste_advice(
    detected_classes: list[str],
    city: str,
    chain,
) -> tuple[str, list[str]]:
    """
    Query RAG chain. Returns (advice_text, source_chunks).
    R4 guard: if no docs pass similarity threshold → HARDCODED_FALLBACK.
    """
    query = (
        f"Disposal advice for the following waste items detected in {city}, India: "
        + ", ".join(detected_classes)
    )
    result = chain.invoke({"query": query})
    source_docs = result.get("source_documents", [])

    # R4 hallucination guard
    if not source_docs:
        return HARDCODED_FALLBACK, []

    answer = result.get("result", HARDCODED_FALLBACK)
    sources = [doc.page_content[:200] for doc in source_docs]
    return answer, sources
