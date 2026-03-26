"""
RAG Service - wraps the ml-models RAG chain for use in FastAPI.
Member 2 (LLM/NLP Lead) owns this file.
"""

import sys
import os
from typing import Optional

from app.config import settings

# Add ml-models to path — ML_MODELS_PATH env var takes priority (set in docker-compose)
sys.path.insert(
    0,
    os.environ.get(
        "ML_MODELS_PATH",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../ml-models")),
    ),
)

_chain = None


def _get_chain():
    global _chain
    if _chain is None:
        from rag.rag_chain import get_chain
        _chain = get_chain(
            persist_dir=settings.chroma_persist_dir,
            groq_api_key=settings.groq_api_key,
        )
    return _chain


def get_disposal_advice(
    detected_class_names: list[str],
    city: str,
) -> tuple[str, list[str]]:
    """
    Returns (advice_text, source_chunks) from the RAG chain.
    Falls back to a static message if chain is unavailable.
    """
    try:
        from rag.rag_chain import query_waste_advice
        chain = _get_chain()
        return query_waste_advice(detected_class_names, city, chain)
    except Exception as e:
        fallback = (
            f"Detected: {', '.join(detected_class_names)}. "
            "Please segregate waste as follows: "
            "Dry recyclables (plastic, paper, metal, glass) → Blue Bin. "
            "Wet food waste → Green Bin. "
            "Hazardous items (batteries, e-waste, medicine) → Red Bin. "
            f"[Note: AI advisor temporarily unavailable: {str(e)[:100]}]"
        )
        return fallback, []
