"""Markdown → safe HTML for CMS content."""

from __future__ import annotations

import html
import re


def md_to_html(md: str) -> str:
    """Minimal markdown subset → HTML (no external deps)."""
    if not md:
        return ""
    text = md.replace("\r\n", "\n")
    # Fenced code blocks
    parts: list[str] = []
    pattern = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)

    def esc(s: str) -> str:
        return html.escape(s)

    last = 0
    for m in pattern.finditer(text):
        parts.append(_inline_blocks(text[last : m.start()]))
        parts.append(f"<pre><code>{esc(m.group(1).rstrip())}</code></pre>")
        last = m.end()
    parts.append(_inline_blocks(text[last:]))
    return "\n".join(p for p in parts if p)


def _inline_blocks(chunk: str) -> str:
    lines = chunk.split("\n")
    out: list[str] = []
    para: list[str] = []
    list_items: list[str] = []

    def flush_para() -> None:
        nonlocal para
        if para:
            out.append("<p>" + _inline(" ".join(para)) + "</p>")
            para = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            out.append("<ul>" + "".join(f"<li>{_inline(i)}</li>" for i in list_items) + "</ul>")
            list_items = []

    for line in lines:
        if not line.strip():
            flush_para()
            flush_list()
            continue
        if line.startswith("### "):
            flush_para()
            flush_list()
            out.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("## "):
            flush_para()
            flush_list()
            out.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("# "):
            flush_para()
            flush_list()
            out.append(f"<h1>{_inline(line[2:])}</h1>")
        elif re.match(r"^[-*] ", line):
            flush_para()
            list_items.append(line[2:])
        else:
            flush_list()
            para.append(line.strip())
    flush_para()
    flush_list()
    return "\n".join(out)


def _inline(text: str) -> str:
    s = html.escape(text)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    s = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        r'<a href="\2" rel="noopener noreferrer">\1</a>',
        s,
    )
    return s
