# RAG Pipeline for Bash Command Grounding

This project now includes a Retrieval-Augmented Generation (RAG) layer that runs before command generation.

## What It Does

1. Stores trusted Bash command examples in a knowledge base.
2. Embeds those examples using a lightweight sentence-transformer model.
3. Indexes embeddings in FAISS for fast similarity search.
4. Retrieves top relevant examples for each user query.
5. Injects retrieved examples into the LLM prompt to reduce hallucinations.

## Main Module

- `src/rag_pipeline.py`
  - Defines `KnowledgeEntry` (category, description, command).
  - Builds command knowledge base from required categories.
  - Creates FAISS index with normalized embeddings.
  - Provides `retrieve(query, top_k)` with LRU-style query cache.
  - Provides `format_for_prompt(...)` to ground the LLM prompt.

## Runtime Flow

Inside `src/app.py` (`/api/execute`):

1. Validate natural-language input.
2. Probe target host context over SSH.
3. **RAG retrieval happens here**:
   - `rag_pipeline.retrieve(natural_language, top_k=3)`
   - `rag_pipeline.format_for_prompt(...)`
4. Send grounded context to `LLMClient.generate_command(...)`.
5. Validate generated command.
6. Execute command via SSH and return results.

## Example Workflow

User asks:
- `show me memory info`

RAG retrieves likely entry:
- Category: `Operating System`
- Description: `show detailed memory information`
- Command: `cat /proc/meminfo`

LLM receives this grounding and outputs:
- `cat /proc/meminfo`

## Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

Added packages:
- `sentence-transformers`
- `faiss-cpu`

## API Output

`/api/execute` now also returns:
- `rag_retrieval`: list of top retrieved knowledge entries used for grounding.

