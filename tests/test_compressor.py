"""Tests for TokenCompressor."""
import pytest
from aip_proxy.compressor import TokenCompressor


def test_level_zero_passthrough():
    tc = TokenCompressor(level=0)
    msgs = [{"role": "user", "content": "Hello world"}]
    result = tc.compress_messages(msgs)
    assert result == msgs


def test_whitespace_normalization():
    tc = TokenCompressor(level=1)
    msgs = [{"role": "user", "content": "Hello\n\n\n\nworld\n\n\n"}]
    result = tc.compress_messages(msgs)
    assert "\n\n\n" not in result[0]["content"]


def test_multiple_spaces_collapsed():
    tc = TokenCompressor(level=1)
    msgs = [{"role": "user", "content": "Hello    world   test"}]
    result = tc.compress_messages(msgs)
    assert "    " not in result[0]["content"]
    assert "Hello world test" == result[0]["content"]


def test_code_block_comments_removed():
    tc = TokenCompressor(level=2)
    code = "```python\n# This is a comment\nx = 1\n# Another comment\ny = 2\n```"
    msgs = [{"role": "user", "content": code}]
    result = tc.compress_messages(msgs)
    assert "# This is a comment" not in result[0]["content"]
    assert "x = 1" in result[0]["content"]
    assert "y = 2" in result[0]["content"]


def test_code_block_preserves_shebangs():
    tc = TokenCompressor(level=2)
    code = "```bash\n#!/bin/bash\necho hello\n```"
    msgs = [{"role": "user", "content": code}]
    result = tc.compress_messages(msgs)
    assert "#!/bin/bash" in result[0]["content"]


def test_abbreviations_level3():
    tc = TokenCompressor(level=3)
    msgs = [{"role": "user", "content": "In order to fix this, due to the fact that it is broken."}]
    result = tc.compress_messages(msgs)
    assert "To fix this" in result[0]["content"]
    assert "Because it is broken" in result[0]["content"]


def test_multimodal_messages():
    tc = TokenCompressor(level=1)
    msgs = [{
        "role": "user",
        "content": [
            {"type": "text", "text": "Hello\n\n\n\nworld"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
        ],
    }]
    result = tc.compress_messages(msgs)
    assert isinstance(result[0]["content"], list)
    assert result[0]["content"][0]["type"] == "text"
    assert "\n\n\n" not in result[0]["content"][0]["text"]
    assert result[0]["content"][1]["type"] == "image_url"


def test_stats_tracking():
    tc = TokenCompressor(level=2)
    msgs = [{"role": "user", "content": "Hello\n\n\n\nworld   test"}]
    tc.compress_messages(msgs)
    savings = tc.get_savings()
    assert savings["calls"] == 1
    assert savings["original_chars"] > 0
    assert savings["savings_pct"] >= 0


def test_preserves_role_and_other_fields():
    tc = TokenCompressor(level=2)
    msgs = [{"role": "system", "content": "You are helpful.", "name": "sys"}]
    result = tc.compress_messages(msgs)
    assert result[0]["role"] == "system"
    assert result[0]["name"] == "sys"


def test_deduplication():
    tc = TokenCompressor(level=2)
    # Create a text with repeated blocks (needs 20+ lines and blocks > 100 chars)
    block = "This is a very long line that has enough characters to trigger deduplication in the compressor module.\n"
    repeated = block * 3  # 3-line block
    text = "Header\n" * 10 + repeated + "Middle\n" * 5 + repeated + "End\n" * 5
    msgs = [{"role": "user", "content": text}]
    result = tc.compress_messages(msgs)
    # Second occurrence should be replaced
    assert "same as above" in result[0]["content"]
