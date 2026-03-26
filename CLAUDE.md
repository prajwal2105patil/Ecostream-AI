# CLAUDE.md — EcoStream AI

## PROJECT OVERVIEW

**EcoStream AI** is a **software-only** smart waste management web platform (no mobile apps, no hardware bins, no React Native).  
It solves the real Indian urban waste problem: **clustered/mixed waste** through three tightly coupled engines:

1. **Vision Engine** – YOLOv11-seg (instance segmentation only)
2. **RAG/LLM Engine** – LangChain + ChromaDB (never hallucinates)
3. **Analytics Engine** – KDE heatmap + predictive routing (WUI formula locked)

**Two UIs**:

- **Citizen Portal** (upload + chat)
- **Government Dashboard** (heatmap + optimized routes)

**Uniqueness (what makes this IEEE-publishable)**: First software-only system that uses instance segmentation + RAG to handle real-world Indian clustered waste and delivers measurable route optimization without any IoT sensors. All metrics in the paper **must** come from the running system.

**Core Constraint**: No feature outside the three engines until all three are production-ready and tested.

## TEAM MAP (Paired Ownership – Redundancy Model)
