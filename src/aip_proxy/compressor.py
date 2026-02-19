"""
Token compressor — the core of AIP Proxy.

Applies multiple compression passes to reduce token count
while preserving semantic content.
"""

import re
import hashlib
from typing import List, Dict, Tuple, Optional


class TokenCompressor:
    """Multi-pass token compressor for LLM prompts."""

    def __init__(self, level: int = 2):
        """
        Args:
            level: Compression aggressiveness (0=off, 1=light, 2=balanced, 3=aggressive)
        """
        self.level = level
        self._seen_blocks = {}  # hash -> shortened version
        self.stats = {"original_chars": 0, "compressed_chars": 0, "calls": 0}

    def compress_messages(self, messages: List[Dict]) -> List[Dict]:
        """Compress a list of chat messages."""
        if self.level == 0:
            return messages

        compressed = []
        for msg in messages:
            new_msg = dict(msg)
            if "content" in msg and isinstance(msg["content"], str):
                original = msg["content"]
                self.stats["original_chars"] += len(original)
                new_msg["content"] = self._compress_text(original)
                self.stats["compressed_chars"] += len(new_msg["content"])
            elif "content" in msg and isinstance(msg["content"], list):
                # Multi-modal messages (text + images)
                new_parts = []
                for part in msg["content"]:
                    if isinstance(part, dict) and part.get("type") == "text":
                        original = part["text"]
                        self.stats["original_chars"] += len(original)
                        new_part = dict(part)
                        new_part["text"] = self._compress_text(original)
                        self.stats["compressed_chars"] += len(new_part["text"])
                        new_parts.append(new_part)
                    else:
                        new_parts.append(part)
                new_msg["content"] = new_parts
            compressed.append(new_msg)

        self.stats["calls"] += 1
        return compressed

    def _compress_text(self, text: str) -> str:
        """Apply compression passes to text."""
        result = text

        # Pass 1: Normalize whitespace (all levels)
        result = self._normalize_whitespace(result)

        if self.level >= 2:
            # Pass 2: Compress code blocks
            result = self._compress_code_blocks(result)

            # Pass 3: Deduplicate repeated content
            result = self._deduplicate_blocks(result)

        if self.level >= 3:
            # Pass 4: Abbreviate common patterns
            result = self._abbreviate_patterns(result)

        return result

    def _normalize_whitespace(self, text: str) -> str:
        """Remove excessive whitespace while preserving structure."""
        # Collapse multiple blank lines to one
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove trailing whitespace on each line
        text = re.sub(r'[ \t]+\n', '\n', text)
        # Collapse multiple spaces (except in code blocks)
        parts = re.split(r'(```[\s\S]*?```)', text)
        for i in range(0, len(parts), 2):  # Only non-code parts
            if i < len(parts):
                parts[i] = re.sub(r'  +', ' ', parts[i])
        return ''.join(parts)

    def _compress_code_blocks(self, text: str) -> str:
        """Compress code within ``` blocks."""
        def compress_code(match):
            lang = match.group(1) or ''
            code = match.group(2)

            # Remove single-line comments
            code = re.sub(r'(?m)^\s*//.*$\n?', '', code)
            code = re.sub(r'(?m)^\s*#(?!!).*$\n?', '', code)

            # Remove empty lines within code
            code = re.sub(r'\n{2,}', '\n', code)

            # Remove trailing whitespace
            code = re.sub(r'[ \t]+\n', '\n', code)

            return f'```{lang}\n{code.strip()}\n```'

        return re.sub(r'```(\w*)\n([\s\S]*?)```', compress_code, text)

    def _deduplicate_blocks(self, text: str) -> str:
        """Replace repeated blocks with reference markers."""
        lines = text.split('\n')
        if len(lines) < 20:
            return text

        # Find repeated blocks of 3+ lines
        block_size = 3
        seen = {}
        result_lines = []
        i = 0

        while i < len(lines):
            if i + block_size <= len(lines):
                block = '\n'.join(lines[i:i + block_size])
                block_hash = hashlib.md5(block.encode()).hexdigest()[:8]

                if block_hash in seen and len(block) > 100:
                    result_lines.append(f'[... same as above ({block_hash}) ...]')
                    i += block_size
                    continue
                elif len(block) > 100:
                    seen[block_hash] = True

            result_lines.append(lines[i])
            i += 1

        return '\n'.join(result_lines)

    def _abbreviate_patterns(self, text: str) -> str:
        """Abbreviate common verbose patterns."""
        abbrevs = [
            (r'Please note that ', ''),
            (r'It is important to note that ', ''),
            (r'As mentioned earlier, ', ''),
            (r'In order to ', 'To '),
            (r'Due to the fact that ', 'Because '),
            (r'At this point in time', 'Now'),
            (r'In the event that ', 'If '),
            (r'For the purpose of ', 'For '),
            (r'With regard to ', 'About '),
            (r'In the context of ', 'In '),
        ]
        for pattern, replacement in abbrevs:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def get_savings(self) -> Dict:
        """Return compression statistics."""
        orig = self.stats["original_chars"]
        comp = self.stats["compressed_chars"]
        saved = orig - comp
        pct = (saved / orig * 100) if orig > 0 else 0
        return {
            "original_chars": orig,
            "compressed_chars": comp,
            "saved_chars": saved,
            "savings_pct": round(pct, 1),
            "calls": self.stats["calls"],
        }
