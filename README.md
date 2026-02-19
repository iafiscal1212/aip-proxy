# AIP Proxy

**Token compression proxy for LLM APIs.** Reduce your AI coding costs by 15-40% without losing quality.

AIP Proxy sits between your AI IDE (Antigravity, Cursor, VS Code, etc.) and the LLM API, compressing prompts on the fly before they reach the model.

## How it works

```
Your IDE  ──>  AIP Proxy (localhost:8090)  ──>  OpenAI / Gemini / Claude API
                    │
                    ├─ Whitespace normalization
                    ├─ Code comment removal
                    ├─ Block deduplication
                    └─ Pattern abbreviation
```

**4 compression passes**, configurable by level:

| Level | Passes | Typical savings |
|-------|--------|-----------------|
| 0 | None (passthrough) | 0% |
| 1 | Whitespace normalization | 5-10% |
| 2 | + Code compression + deduplication | 15-25% |
| 3 | + Pattern abbreviation | 25-40% |

## Install

```bash
pip install aip-proxy
```

## Quick start

```bash
# Start proxy targeting OpenAI
aip-proxy start --target https://api.openai.com/v1 --port 8090

# Or targeting Google Gemini
aip-proxy start --target https://generativelanguage.googleapis.com --port 8090

# Or any OpenAI-compatible API
aip-proxy start --target https://api.anthropic.com --port 8090
```

Then change your IDE's API endpoint to `http://localhost:8090/v1`.

## Usage with Antigravity

1. Install: `pip install aip-proxy`
2. Start: `aip-proxy start --target https://generativelanguage.googleapis.com --port 8090`
3. In Antigravity settings, set API endpoint to `http://localhost:8090`
4. Done — you'll see savings in the proxy stats

## Usage with Cursor / VS Code

1. Install: `pip install aip-proxy`
2. Start: `aip-proxy start --target https://api.openai.com/v1 --port 8090`
3. In your IDE settings, change the API base URL to `http://localhost:8090/v1`
4. Keep your API key as usual — the proxy forwards it transparently

## Options

```bash
aip-proxy start --help

Options:
  --target, -t    Target API URL (required)
  --port, -p      Port to listen on (default: 8090)
  --host          Host to bind (default: 127.0.0.1)
  --level, -l     Compression: 0=off, 1=light, 2=balanced, 3=aggressive (default: 2)
  --no-cache      Disable response caching
  --cache-ttl     Cache TTL in seconds (default: 300)
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Proxy status and basic stats |
| `GET /stats` | Detailed compression and cache statistics |
| `* /{path}` | Proxied to target API |

## Python API

```python
from aip_proxy import TokenCompressor

tc = TokenCompressor(level=2)
messages = [
    {"role": "user", "content": "your long prompt here..."}
]
compressed = tc.compress_messages(messages)
print(tc.get_savings())
# {'original_chars': 1500, 'compressed_chars': 1100, 'saved_chars': 400, 'savings_pct': 26.7, 'calls': 1}
```

## How does it save money?

LLM APIs charge per token. A typical coding session sends thousands of tokens in context — much of it is:

- Redundant whitespace and blank lines
- Comments in code blocks (the model doesn't need them)
- Repeated code blocks across messages
- Verbose filler phrases

AIP Proxy removes this noise while preserving the semantic content the model needs.

## License

MIT
