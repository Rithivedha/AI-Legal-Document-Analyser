import urllib.request
import urllib.error
import json

key = "sk-EPNqN9B5i0meqxurPh2QgR3fjcL6lgFoYUy4MuQv9xpukceP"

def test_url(name, url, headers, data=None):
    try:
        req = urllib.request.Request(url, headers=headers, data=data)
        with urllib.request.urlopen(req) as resp:
            print(f"{name}: SUCCESS ({resp.status})")
            return True
    except urllib.error.HTTPError as e:
        err = e.read().decode('utf-8', errors='ignore')
        print(f"{name}: HTTP {e.code} -> {err[:150]}")
    except Exception as e:
        print(f"{name}: Exception -> {e}")
    return False

# Test OpenAI
test_url("OpenAI Models", "https://api.openai.com/v1/models", {"Authorization": f"Bearer {key}"})

# Test Anthropic
test_url("Anthropic", "https://api.anthropic.com/v1/messages", {
    "x-api-key": key,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}, data=b'{"model":"claude-3-haiku-20240307","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}')

# Test Groq
test_url("Groq", "https://api.groq.com/openai/v1/models", {
    "Authorization": f"Bearer {key}",
    "User-Agent": "Mozilla/5.0"
})

# Test Gemini (in case key was used as query param)
test_url("Gemini", f"https://generativelanguage.googleapis.com/v1beta/models?key={key}", {})
