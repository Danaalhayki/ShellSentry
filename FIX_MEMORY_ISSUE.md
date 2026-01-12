# Fix: "Model requires more system memory" Error

## 🔍 The Problem

Your system has **4.9 GiB RAM** but the model needs **5.5 GiB RAM**. LLM models must load into RAM (system memory) to run - they can't just run from hard disk.

## ✅ Solutions (Choose One)

### Solution 1: Use a Smaller Model (Easiest) ⭐ Recommended

Use a smaller, quantized model that fits in your RAM:

```bash
# Remove the large model
ollama rm llama2

# Pull a smaller model (these use less RAM)
ollama pull llama3.2:1b        # ~1.3 GB - Very small, fast
ollama pull llama3.2:3b         # ~2.0 GB - Good balance
ollama pull phi3:mini           # ~2.3 GB - Microsoft's small model
ollama pull gemma:2b            # ~1.4 GB - Google's small model
```

Then update your `.env`:
```env
LLM_MODEL=llama3.2:1b
# or
LLM_MODEL=phi3:mini
# or
LLM_MODEL=gemma:2b
```

**Recommended:** Start with `llama3.2:1b` - it's the smallest and will definitely work!

---

### Solution 2: Use Cloud Service (No Memory Issues)

Switch to a cloud service - they handle the memory:

#### Groq (Free, Very Fast)
1. Sign up: https://console.groq.com/
2. Get API key
3. Update `.env`:
   ```env
   LLM_API_KEY=your-groq-key
   LLM_API_BASE_URL=https://api.groq.com/openai/v1
   LLM_MODEL=llama-3.1-8b-instant
   ```

#### Together AI (Free Tier)
1. Sign up: https://together.ai/
2. Get API key
3. Update `.env`:
   ```env
   LLM_API_KEY=your-together-key
   LLM_API_BASE_URL=https://api.together.xyz/v1
   LLM_MODEL=meta-llama/Llama-3.2-1B-Instruct-Turbo
   ```

---

### Solution 3: Increase Virtual Memory (Windows - Slower)

This allows Windows to use disk space as "fake RAM" but it will be **much slower**:

1. Open **Control Panel** → **System** → **Advanced System Settings**
2. Click **Settings** under Performance
3. Go to **Advanced** tab
4. Click **Change** under Virtual Memory
5. Uncheck "Automatically manage paging file size"
6. Set **Custom size**: 
   - Initial: 8192 MB (8 GB)
   - Maximum: 16384 MB (16 GB)
7. Click **Set** → **OK** → Restart computer

⚠️ **Warning:** This will be slow because it uses disk instead of RAM.

---

### Solution 4: Use Quantized Model (Advanced)

Download a quantized version that uses less memory:

```bash
# Try these smaller quantized models
ollama pull llama3.2:1b-instruct-q4_0
ollama pull phi3:mini-q4
```

---

## 🎯 Quick Fix (Do This Now)

**Easiest solution - use a smaller model:**

```bash
# Pull the smallest model
ollama pull llama3.2:1b

# Update your .env file
# Change: LLM_MODEL=llama2
# To:     LLM_MODEL=llama3.2:1b
```

Then restart your Flask app and try again!

---

## 📊 Model Size Comparison

| Model | RAM Needed | Quality | Speed |
|-------|-----------|---------|-------|
| llama3.2:1b | ~1.3 GB | Good | Very Fast |
| llama3.2:3b | ~2.0 GB | Better | Fast |
| phi3:mini | ~2.3 GB | Good | Fast |
| llama2 (7b) | ~5.5 GB | Best | Medium |

**For your 4.9 GB RAM:** Use `llama3.2:1b` or `phi3:mini`

---

## ✅ Test After Fix

```bash
python test_llm.py
```

If it works, you'll see:
```
[SUCCESS] API call successful!
```

