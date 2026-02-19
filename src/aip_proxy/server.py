"""
AIP Proxy Server — FastAPI-based OpenAI-compatible proxy.

Sits between your AI IDE and the LLM API, compressing tokens
to reduce costs by 15-40%.
"""

import time
import json
import httpx
from typing import Optional
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse

from .compressor import TokenCompressor
from .cache import ResponseCache
from .stats import StatsTracker


def create_app(
    target_url: str,
    compression_level: int = 2,
    cache_enabled: bool = True,
    cache_ttl: int = 300,
) -> FastAPI:
    """Create the proxy FastAPI app."""

    app = FastAPI(
        title="AIP Proxy",
        description="Token compression proxy for LLM APIs",
        version="0.1.0",
    )

    compressor = TokenCompressor(level=compression_level)
    cache = ResponseCache(enabled=cache_enabled, ttl=cache_ttl)
    stats = StatsTracker()

    # Normalize target URL
    target = target_url.rstrip("/")

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "target": target,
            "compression_level": compression_level,
            "stats": stats.summary(),
        }

    @app.get("/stats")
    async def get_stats():
        return {
            "compressor": compressor.get_savings(),
            "cache": cache.get_stats(),
            "requests": stats.summary(),
        }

    @app.api_route(
        "/{path:path}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    )
    async def proxy(request: Request, path: str):
        """Proxy all requests to the target API with token compression."""
        t0 = time.time()
        url = f"{target}/{path}"

        # Read request body
        body = await request.body()
        headers = dict(request.headers)

        # Remove hop-by-hop headers
        for h in ["host", "content-length", "transfer-encoding"]:
            headers.pop(h, None)

        is_chat = path.endswith("/chat/completions") and request.method == "POST"
        is_streaming = False
        original_body = body

        if is_chat and body:
            try:
                data = json.loads(body)
                is_streaming = data.get("stream", False)

                # Check cache for non-streaming requests
                if not is_streaming and cache.enabled:
                    cached = cache.get(data)
                    if cached is not None:
                        stats.record(
                            path=path,
                            duration=time.time() - t0,
                            cached=True,
                        )
                        return JSONResponse(content=cached)

                # Compress messages
                if "messages" in data:
                    data["messages"] = compressor.compress_messages(data["messages"])
                    body = json.dumps(data).encode()

            except (json.JSONDecodeError, KeyError):
                pass  # Forward as-is if not valid JSON

        # Forward to target
        async with httpx.AsyncClient(timeout=300.0) as client:
            if is_streaming:
                # Stream response back
                upstream = await client.send(
                    client.build_request(
                        method=request.method,
                        url=url,
                        headers=headers,
                        content=body,
                    ),
                    stream=True,
                )

                async def stream_generator():
                    async for chunk in upstream.aiter_bytes():
                        yield chunk
                    await upstream.aclose()
                    stats.record(
                        path=path,
                        duration=time.time() - t0,
                        cached=False,
                        streamed=True,
                    )

                return StreamingResponse(
                    stream_generator(),
                    status_code=upstream.status_code,
                    headers=dict(upstream.headers),
                    media_type=upstream.headers.get("content-type"),
                )
            else:
                # Regular request
                resp = await client.request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    content=body,
                )

                # Cache successful chat responses
                if is_chat and resp.status_code == 200 and cache.enabled:
                    try:
                        resp_data = resp.json()
                        original_data = json.loads(original_body)
                        cache.put(original_data, resp_data)
                    except (json.JSONDecodeError, ValueError):
                        pass

                stats.record(
                    path=path,
                    duration=time.time() - t0,
                    cached=False,
                    status=resp.status_code,
                )

                # Forward response
                response_headers = dict(resp.headers)
                for h in ["content-encoding", "transfer-encoding", "content-length"]:
                    response_headers.pop(h, None)

                return Response(
                    content=resp.content,
                    status_code=resp.status_code,
                    headers=response_headers,
                    media_type=resp.headers.get("content-type"),
                )

    return app
