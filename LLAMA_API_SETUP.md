# How to Get LLaMA API Link - Step by Step

## 🎯 Quick Answer

**For Local LLaMA (Free, Recommended):**
- API Link: `http://localhost:11434/v1`
- You create this yourself by installing Ollama

**For Cloud LLaMA (Paid/Free Tier):**
- Sign up at a service provider
- They give you an API endpoint URL
- Use that URL in your `.env` file

---

## Option 1: Local LLaMA with Ollama (FREE) ⭐ Recommended

### Step 1: Download Ollama
- **Windows:** https://ollama.ai/download/windows
- **Mac:** https://ollama.ai/download/mac
- **Linux:** Run: `curl -fsSL https://ollama.ai/install.sh | sh`

### Step 2: Install a Model
Open terminal/command prompt and run:
```bash
ollama pull llama2
```

### Step 3: Start Ollama Server
```bash
ollama serve
```
Keep this running! The server will be at `http://localhost:11434`

### Step 4: Update Your .env File
Open your `.env` file and change these lines:
```env
LLM_API_TYPE=openai
LLM_API_KEY=ollama
LLM_API_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama2
```

**That's it!** The API link is `http://localhost:11434/v1` - it's on your own computer.

---

## Option 2: Cloud LLaMA Services

### Together AI (Free Tier Available)

1. **Sign up:** https://together.ai/
2. **Get API key:** Go to API Keys section
3. **Find endpoint:** Usually `https://api.together.xyz/v1`
4. **Update .env:**
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
   LLM_MODEL=llama2-70b-4096
   ```

### Replicate

1. **Sign up:** https://replicate.com/
2. **Get API token:** https://replicate.com/account/api-tokens
3. **Update .env:**
   ```env
   LLM_API_KEY=your-replicate-token
   LLM_API_BASE_URL=https://api.replicate.com/v1
   LLM_MODEL=meta/llama-2-7b-chat
   ```

---

## 📝 Summary: What Goes in .env

### For Local Ollama:
```env
LLM_API_TYPE=openai
LLM_API_KEY=ollama
LLM_API_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama2
```

### For Cloud Service:
```env
LLM_API_TYPE=openai
LLM_API_KEY=your-api-key-from-service
LLM_API_BASE_URL=https://api.service.com/v1
LLM_MODEL=model-name-from-service
```

---

## ✅ Test Your Setup

After updating `.env`, test it:
```bash
python test_llm.py
```

If it works, you'll see:
```
[SUCCESS] API call successful!
Generated command: netstat -nlutp
```

---

## 🔍 Where is the API Link?

- **Local:** You create it by running `ollama serve` → `http://localhost:11434/v1`
- **Cloud:** Provided by the service when you sign up (check their documentation)

The "link" is just the URL where the API is running!

