# 🔑 API Keys Setup Guide

## After pulling from GitHub on Raspberry Pi:

### Step 1: Copy the template
```bash
cp api_keys_template.py api_keys.py
```

### Step 2: Edit with nano
```bash
nano api_keys.py
```

### Step 3: Add your API keys
Replace the placeholder text with your actual Google Gemini API keys:

```python

API_KEYS = [
    "AIzaSyCdwloWxhjYb7sHMPRVvsrFigPa2iciR8k",  # Your working key
    "AIzaSyAGw82x3qbRMf0aF1XbUbyr1-N8cn-tfus",
    "AIzaSyC9TzuoMFNm0UeCyAPeIlxKWxZRrYhzedY",
    "AIzaSyCB_KAyLJ34m26QlN2AzFnhDKqmQ9CXJVs",
    "AIzaSyAJJ7snqwJWG4sQ7-0tSSqFph8pSRGl-Y8",
]
```

### Step 4: Save and exit
- Press `Ctrl + X`
- Press `Y` (yes to save)
- Press `Enter` (confirm filename)

### Step 5: Verify
```bash
python3 test_api_rotation.py
```

You should see successful AI responses!

---

## Quick Commands for Pi:
```bash
# Pull latest code
git pull origin main

# Setup API keys
cp api_keys_template.py api_keys.py
nano api_keys.py
# (Add your keys, then Ctrl+X, Y, Enter)

# Test
python3 test_api_rotation.py

# Run OMNIS
python3 main.py
```
