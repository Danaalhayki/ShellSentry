# Setting Up Local LLM (Alternative to OpenAI)

If you don't have OpenAI credits or want to use a local LLM, here's how to set it up:

## Option 1: Using Ollama (Recommended for Local Testing)

### Step 1: Install Ollama
- **Windows:** Download from https://ollama.ai/download
- **Mac/Linux:** `curl -fsSL https://ollama.ai/install.sh | sh`

### Step 2: Pull a Model
```bash
ollama pull llama2
# or
ollama pull mistral
# or
ollama pull codellama
```

### Step 3: Start Ollama Server
```bash
ollama serve
```

### Step 4: Update .env File
```env
LLM_API_TYPE=openai
LLM_API_KEY=ollama  # Not actually used, but required
LLM_API_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama2  # or mistral, codellama, etc.
```

### Step 5: Test
```bash
python test_llm.py
```

## Option 2: Using Other Local LLM Servers

### LocalAI
1. Install LocalAI: https://localai.io/
2. Start the server
3. Update `.env`:
   ```
   LLM_API_BASE_URL=http://localhost:8080/v1
   LLM_MODEL=your-model-name
   ```

### LM Studio
1. Download LM Studio: https://lmstudio.ai/
2. Load a model and start the local server
3. Update `.env`:
   ```
   LLM_API_BASE_URL=http://localhost:1234/v1
   LLM_MODEL=your-model-name
   ```

## Option 3: Use OpenAI-Compatible API

Many services provide OpenAI-compatible APIs:
- **Together AI:** https://together.ai/
- **Anthropic Claude:** https://console.anthropic.com/
- **Google Gemini:** https://makersuite.google.com/

Just update `LLM_API_BASE_URL` and `LLM_API_KEY` in your `.env` file.

## Testing Your Setup

After configuring, run:
```bash
python test_llm.py
```

This will verify your LLM connection is working.

