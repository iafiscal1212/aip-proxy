"""
AIP Proxy — Token Compression Proxy for LLM APIs
==================================================

Sits between your AI IDE and the model API, compressing tokens
to reduce costs by 15-40% without losing quality.

Quick start:
    pip install aip-proxy
    aip-proxy start --target https://api.openai.com/v1 --port 8090

Then point your IDE's API endpoint to http://localhost:8090/v1

Author: Carmen Esteban
License: MIT
"""

__version__ = "0.1.0"
__author__ = "Carmen Esteban"

from .compressor import TokenCompressor
from .cache import ResponseCache
from .stats import StatsTracker

__all__ = ["TokenCompressor", "ResponseCache", "StatsTracker"]
