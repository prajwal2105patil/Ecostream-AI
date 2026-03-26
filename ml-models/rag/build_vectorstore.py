"""
Vector Store Builder
Member 2 (LLM/NLP Lead) owns this file.

Ingests all documents from data/knowledge_base/ into ChromaDB.

Usage:
    python ml-models/rag/build_vectorstore.py

Run this once after adding new documents to the knowledge base.
"""

import os
from pathlib import Path
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings


KNOWLEDGE_BASE_DIR = "data/knowledge_base"
CHROMA_PERSIST_DIR = "data/chroma_db"
COLLECTION_NAME = "waste_knowledge"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def load_documents(base_dir: str):
    docs = []
    for filepath in Path(base_dir).rglob("*"):
        if filepath.suffix == ".txt":
            loader = TextLoader(str(filepath), encoding="utf-8")
            docs.extend(loader.load())
        elif filepath.suffix == ".pdf":
            loader = PyPDFLoader(str(filepath))
            docs.extend(loader.load())
    print(f"Loaded {len(docs)} documents from {base_dir}")
    return docs


def build_vectorstore():
    docs = load_documents(KNOWLEDGE_BASE_DIR)
    if not docs:
        print("No documents found. Add .txt or .pdf files to data/knowledge_base/")
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
    )
    chunks = splitter.split_documents(docs)
    print(f"Split into {len(chunks)} chunks")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
        collection_name=COLLECTION_NAME,
    )
    print(f"Vector store built with {vectorstore._collection.count()} vectors")
    print(f"Persisted to: {CHROMA_PERSIST_DIR}")


if __name__ == "__main__":
    build_vectorstore()
