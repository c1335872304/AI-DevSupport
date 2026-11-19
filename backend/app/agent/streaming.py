"""Bounded semantic units for live output, not a whole-answer buffer."""
from __future__ import annotations

import ast
import re


_PYTHON_FENCE = re.compile(r"(?ims)^(?P<fence>`{3,}|~{3,})(?:python|py)[ \t]*\r?\n(?P<code>.*?)^(?P=fence)[ \t]*(?=\r?$)")
_CREDENTIAL_NAME = re.compile(r"(?:.*_)?(?:token|api_?key|password|secret|credential)(?:_value)?$", re.IGNORECASE)
_OUTPUT_CALLS = {"print", "debug", "info", "warning", "error", "critical", "exception", "log", "write"}


def remove_credential_output_examples(answer: str) -> str:
    """Replace statements that print or log a credential in a Python example."""
    def sanitize(match: re.Match[str]) -> str:
        code = match.group("code")
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return match.group(0)
        encoded = code.encode()
        starts = [0]
        for line in encoded.splitlines(keepends=True):
            starts.append(starts[-1] + len(line))
        replacements = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
                continue
            call = node.value
            function = call.func
            name = function.id if isinstance(function, ast.Name) else getattr(function, "attr", "")
            arguments = [*call.args, *(keyword.value for keyword in call.keywords)]
            if name in _OUTPUT_CALLS and any(
                (isinstance(value, ast.Name) and _CREDENTIAL_NAME.fullmatch(value.id))
                or (isinstance(value, ast.Constant) and isinstance(value.value, str) and _CREDENTIAL_NAME.fullmatch(value.value))
                for argument in arguments
                for value in ast.walk(argument)
            ):
                start = starts[node.lineno - 1] + node.col_offset
                end = starts[node.end_lineno - 1] + node.end_col_offset
                replacements.append((start, end))
        for start, end in sorted(replacements, reverse=True):
            encoded = encoded[:start] + b"pass" + encoded[end:]
        sanitized = encoded.decode()
        start = match.start("code") - match.start()
        end = match.end("code") - match.start()
        return match.group(0)[:start] + sanitized + match.group(0)[end:]

    return _PYTHON_FENCE.sub(sanitize, answer)


class StreamUnitBuffer:
    """Wait for a sentence/line or closed fenced block before checking it.

    Provider chunks are arbitrary: neither a credential nor a claim is safe to
    validate token by token. Preserve whitespace and code fences across chunks.
    An unusually long unfinished unit fails rather than bypassing validation.
    """

    def __init__(self, max_chars: int = 64000) -> None:
        self.pending = ""
        self.max_chars = max_chars

    def feed(self, text: str, *, final: bool = False) -> list[str]:
        self.pending += text
        if len(self.pending) > self.max_chars:
            raise ValueError("unfinished streaming unit exceeds safe buffer limit")
        ends: list[int] = []
        offset = 0
        fence: tuple[str, int] | None = None
        for line in self.pending.splitlines(keepends=True):
            complete = line.endswith(("\n", "\r"))
            marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)", line)
            if marker:
                symbol, length = marker[1][0], len(marker[1])
                if fence is None:
                    fence = (symbol, length)
                elif symbol == fence[0] and length >= fence[1] and not marker[2].strip() and (complete or final):
                    fence = None
                    ends.append(offset + len(line))
                offset += len(line)
                continue
            if fence is None:
                # Citation footers are checked/rebuilt as complete lines, never
                # leaked with a partially received source number or file name.
                if not line.lstrip().startswith("来源#"):
                    for index, char in enumerate(line):
                        following = line[index + 1:index + 2]
                        if char in "。！？" or (char in ".!?" and following and following.isspace()):
                            ends.append(offset + index + 1)
                if complete:
                    ends.append(offset + len(line))
            offset += len(line)
        if final and self.pending:
            ends.append(len(self.pending))
        units, start = [], 0
        for end in sorted(set(ends)):
            if end > start:
                units.append(self.pending[start:end])
                start = end
        self.pending = self.pending[start:]
        return units


def without_citation_footer(answer: str) -> str:
    """The gate sees canonical citations; append the actual footer once at end."""
    return "\n".join(line for line in answer.splitlines() if not line.lstrip().startswith("来源#")).rstrip()
