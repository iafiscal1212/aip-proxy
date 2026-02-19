"""
CLI entry point for AIP Proxy.

Usage:
    aip-proxy start --target https://api.openai.com/v1 --port 8090
    aip-proxy start --target https://generativelanguage.googleapis.com --port 8090
    aip-proxy stats
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="aip-proxy",
        description="AIP Proxy — Token compression proxy for LLM APIs",
    )
    subparsers = parser.add_subparsers(dest="command")

    # start command
    start_parser = subparsers.add_parser("start", help="Start the proxy server")
    start_parser.add_argument(
        "--target", "-t",
        required=True,
        help="Target API URL (e.g. https://api.openai.com/v1)",
    )
    start_parser.add_argument(
        "--port", "-p",
        type=int,
        default=8090,
        help="Port to listen on (default: 8090)",
    )
    start_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    start_parser.add_argument(
        "--level", "-l",
        type=int,
        default=2,
        choices=[0, 1, 2, 3],
        help="Compression level: 0=off, 1=light, 2=balanced, 3=aggressive (default: 2)",
    )
    start_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable response caching",
    )
    start_parser.add_argument(
        "--cache-ttl",
        type=int,
        default=300,
        help="Cache TTL in seconds (default: 300)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "start":
        _run_server(args)


def _run_server(args):
    """Start the proxy server."""
    import uvicorn
    from .server import create_app

    print(f"""
╔══════════════════════════════════════════════╗
║           AIP Proxy v0.1.0                   ║
║   Token Compression for LLM APIs             ║
╚══════════════════════════════════════════════╝

  Target:      {args.target}
  Listening:   http://{args.host}:{args.port}
  Compression: Level {args.level}
  Cache:       {'OFF' if args.no_cache else f'ON (TTL {args.cache_ttl}s)'}

  Point your IDE to: http://{args.host}:{args.port}/v1
  Health check:      http://{args.host}:{args.port}/health
  Stats:             http://{args.host}:{args.port}/stats
""")

    app = create_app(
        target_url=args.target,
        compression_level=args.level,
        cache_enabled=not args.no_cache,
        cache_ttl=args.cache_ttl,
    )

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
