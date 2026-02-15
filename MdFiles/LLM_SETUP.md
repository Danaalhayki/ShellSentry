# LLM Setup Guide

This guide covers how to configure the Large Language Model (LLM) for ShellSentry. You can use either a local LLM (free) or a cloud-based service.

## Quick Start

**For Local LLM (Free, Recommended):**
- Use Ollama: `http://localhost:11434/v1`
- No API key required

**For Cloud Services:**
- Sign up at a service provider
- Get API key and endpoint URL
- Configure in `.env` file

---

## Option 1: Local LLM with Ollama (FREE) ⭐ Recommended

### Step 1: Install Ollama

- **Windows:** Download from https://ollama.ai/download/windows
- **Mac:** Download from https://ollama.ai/download/mac
- **Linux:** Run: `curl -fsSL https://ollama.ai/install.sh | sh`

### Step 2: Download a Model

Open terminal/command prompt and run:
```bash
# Small models (recommended for limited RAM)
ollama pull llama3.2:1b        # ~1.3 GB - Very small, fast
ollama pull llama3.2:3b         # ~2.0 GB - Good balance
ollama pull phi3:mini           # ~2.3 GB - Microsoft's small model

# Medium models (if you have more RAM)
ollama pull llama2              # ~3.8 GB
ollama pull mistral             # ~4.1 GB
ollama pull codellama           # ~3.8 GB
```

**Note:** Choose a model that fits your available RAM. Models must load entirely into memory.

### Step 3: Start Ollama Server

```bash
ollama serve
```

Keep this running! The server will be available at `http://localhost:11434`

### Step 4: Update Your .env File

Open your `.env` file and configure:
```env
LLM_API_TYPE=openai
LLM_API_KEY=ollama
LLM_API_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.2:1b  # Use the model you downloaded
```

**That's it!** The API is now running on your local machine.

---

## Option 2: Other Local LLM Servers

### LocalAI

1. Install LocalAI: https://localai.io/
2. Start the server
3. Update `.env`:
   ```env
   LLM_API_BASE_URL=http://localhost:8080/v1
   LLM_MODEL=your-model-name
   ```

### LM Studio

1. Download LM Studio: https://lmstudio.ai/
2. Load a model and start the local server
3. Update `.env`:
   ```env
   LLM_API_BASE_URL=http://localhost:1234/v1
   LLM_MODEL=your-model-name
   ```

---

## Option 3: Cloud LLM Services

### OpenAI (Paid)

1. **Sign up:** https://platform.openai.com/
2. **Get API key:** https://platform.openai.com/api-keys
3. **Update .env:**
   ```env
   LLM_API_TYPE=openai
   LLM_API_KEY=sk-your-openai-key
   LLM_API_BASE_URL=https://api.openai.com/v1
   LLM_MODEL=gpt-4o-mini
   ```

### Together AI (Free Tier Available)

1. **Sign up:** https://together.ai/
2. **Get API key:** Go to API Keys section
3. **Update .env:**
   ```env
   LLM_API_KEY=your-together-api-key
   LLM_API_BASE_URL=https://api.together.xyz/v1
   LLM_MODEL=meta-llama/Llama-2-7b-chat-hf
   ```

### Groq (Very Fast, Free Tier)

1. **Sign up:** https://console.groq.com/
2. **Get API key:** Create API key in dashboard
3. **Update .env:**
   ```env
   LLM_API_KEY=your-groq-api-key
   LLM_API_BASE_URL=https://api.groq.com/openai/v1
   LLM_MODEL=llama-3.1-8b-instant
   ```

### Anthropic Claude

1. **Sign up:** https://console.anthropic.com/
2. **Get API key:** API Keys section
3. **Update .env:**
   ```env
   LLM_API_KEY=your-claude-key
   LLM_API_BASE_URL=https://api.anthropic.com/v1
   LLM_MODEL=claude-3-haiku-20240307
   ```

---

## Configuration Summary

Configuration is read from the project root `.env` file (used by `src/config.py`).

### For Local Ollama:
```env
LLM_API_TYPE=openai
LLM_API_KEY=ollama
LLM_API_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.2:1b
```

### For Cloud Service:
```env
LLM_API_TYPE=openai
LLM_API_KEY=your-api-key-from-service
LLM_API_BASE_URL=https://api.service.com/v1
LLM_MODEL=model-name-from-service
```

---

## Testing Your Setup

After configuring, test the connection:
```bash
python test_llm.py
```

If successful, you'll see:
```
[SUCCESS] API call successful!
Generated command: netstat -nlutp
```

---

## Troubleshooting

### "Model requires more system memory"
- Use a smaller model (e.g., `llama3.2:1b` instead of `llama2`)
- See model size comparison below

### "Connection refused" or "Failed to connect"
- Ensure Ollama server is running: `ollama serve`
- Check that the port matches your `.env` configuration
- Verify firewall settings

### "Invalid API key"
- Double-check your API key in `.env`
- For local Ollama, use `LLM_API_KEY=ollama` (any value works)
- For cloud services, ensure the key is correct and has credits/quota

### "Model not found"
- Ensure you've downloaded the model: `ollama pull <model-name>`
- Verify the model name in `.env` matches exactly

---

## Model Size Comparison

| Model | RAM Needed | Quality | Speed |
|-------|-----------|---------|-------|
| llama3.2:1b | ~1.3 GB | Good | Very Fast |
| llama3.2:3b | ~2.0 GB | Better | Fast |
| phi3:mini | ~2.3 GB | Good | Fast |
| llama2 (7b) | ~5.5 GB | Best | Medium |

**Recommendation:** Start with `llama3.2:1b` if you have limited RAM (< 4 GB available).

---

## Additional Resources

- **Ollama Documentation:** https://ollama.ai/docs
- **OpenAI API Docs:** https://platform.openai.com/docs
- **Together AI Docs:** https://docs.together.ai/
- **Groq Documentation:** https://console.groq.com/docs

