"""
helpers.py — building blocks for the CE-RCA composite report.

Two responsibilities:

1. **Markdown → HTML (verbatim).** CE Health and perf-audit both ship markdown.
   We render that markdown to HTML for their tab panes WITHOUT taking a hard
   dependency on the `markdown` PyPI package (skills ship as files, not a pinned
   Python project). This renderer is vendored from cvr-rca's render.py
   (`render_markdown_to_html`) and extended with blockquote + fenced-code-block
   support to match the v1.22 conversion mapping in visual_kit.md. Every
   section, every subsection, every table cell, every word is preserved — the
   sub-skill's own structure is the structure of its tab. Heading IDs are
   injected with a configurable prefix (e.g. `cehealth-`, `perfaudit-`) so
   cross-tab anchors stay namespaced and stable.

2. **CVR-RCA tab extraction.** CVR-RCA writes a full standalone report.html
   (its own 2-tab CVR + perf-audit layout, or single-tab flat). The master
   shows perf-audit as its OWN peer tab, so from CVR-RCA's report we extract
   only the CVR content — the inner HTML of `<div id="tab-cvr-rca">`, falling
   back to the `.container` body for single-tab reports — plus the Plotly
   `<script>` blocks (which live at the end of <body>, outside the tab pane)
   so the charts still render in the composite. Content is preserved verbatim;
   only the wrapper chrome is stripped.

The master is a composer, not an editor — nothing here paraphrases, summarizes,
or restructures sub-skill output.
"""
from __future__ import annotations

import re
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Slug + inline markdown
# ─────────────────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """Turn a heading like '5. Coverage + Matchmaking' into 'coverage-matchmaking'.

    Strips a leading numbered prefix ('5. ', '4a. '), drops markdown emphasis,
    lowercases, replaces non-alphanumerics with hyphens, collapses runs.
    """
    text = re.sub(r"^\s*[0-9]+[a-z]?\.\s*", "", text)   # drop leading "5. " / "4a. "
    text = re.sub(r"[`*_]", "", text)                    # strip md emphasis
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    return text or "section"


def _md_inline(text: str) -> str:
    """Inline conversions: links, code, bold, italic. Order matters."""
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def _md_parse_table(lines: list[str], start: int) -> tuple[str, int]:
    """Parse a GFM pipe table starting at `lines[start]`. Returns (html, consumed)."""
    def cells(row: str) -> list[str]:
        row = row.strip().strip("|")
        return [c.strip() for c in row.split("|")]

    header_cells = cells(lines[start])
    i = start + 2  # skip header + alignment row
    rows: list[list[str]] = []
    while i < len(lines) and "|" in lines[i] and lines[i].strip():
        rows.append(cells(lines[i]))
        i += 1
    out = ['<div class="md-table-wrap"><table class="md-table"><thead><tr>']
    for cell in header_cells:
        out.append(f"<th>{_md_inline(cell)}</th>")
    out.append("</tr></thead><tbody>")
    for row in rows:
        out.append("<tr>")
        for cell in row:
            out.append(f"<td>{_md_inline(cell)}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out), i - start


def _md_parse_list(lines: list[str], start: int, ordered: bool) -> tuple[str, int]:
    """Parse a contiguous list block. Returns (html, consumed)."""
    pat = re.compile(r"^\s*\d+\.\s+(.*)$" if ordered else r"^\s*[-*]\s+(.*)$")
    items: list[str] = []
    i = start
    while i < len(lines):
        m = pat.match(lines[i])
        if not m:
            break
        items.append(_md_inline(m.group(1)))
        i += 1
    tag = "ol" if ordered else "ul"
    return f"<{tag}>" + "".join(f"<li>{it}</li>" for it in items) + f"</{tag}>", i - start


def _md_parse_blockquote(lines: list[str], start: int) -> tuple[str, int]:
    """Parse a contiguous blockquote block. Returns (html, consumed)."""
    body: list[str] = []
    i = start
    while i < len(lines) and re.match(r"^\s*>\s?", lines[i]):
        body.append(re.sub(r"^\s*>\s?", "", lines[i]))
        i += 1
    return f"<blockquote>{_md_inline(' '.join(body))}</blockquote>", i - start


def _md_parse_fenced_code(lines: list[str], start: int) -> tuple[str, int]:
    """Parse a ```-fenced code block. Returns (html, consumed). Content verbatim."""
    fence = re.match(r"^\s*```", lines[start])
    body: list[str] = []
    i = start + 1
    while i < len(lines) and not re.match(r"^\s*```", lines[i]):
        body.append(lines[i])
        i += 1
    i += 1  # consume closing fence
    escaped = "\n".join(body).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"<pre><code>{escaped}</code></pre>", i - start


def render_markdown_to_html(md: str, anchor_prefix: str = "") -> str:
    """Render sub-skill markdown to HTML, verbatim.

    Supported (matches visual_kit.md "Perf-audit tab rendering" mapping):
      - ATX headings (#..######) with auto-injected id="<anchor_prefix><slug>"
      - GFM pipe tables → <table class="md-table">
      - Unordered (- *) and ordered (1.) lists
      - Blockquotes (> quote)
      - Fenced code blocks (``` ... ```)
      - Bold (**), italic (*), inline code (`), links ([t](u))
      - Horizontal rules (---)
      - Paragraphs (blank-line separated)
      - HTML comment passthrough (sub-skills use <!-- markers -->)
    """
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # HTML comment passthrough
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            out.append(stripped)
            i += 1
            continue

        # Fenced code block
        if re.match(r"^\s*```", line):
            html, consumed = _md_parse_fenced_code(lines, i)
            out.append(html)
            i += consumed
            continue

        # ATX heading
        m = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if m:
            level = len(m.group(1))
            text = m.group(2)
            slug = slugify(text)
            anchor = f' id="{anchor_prefix}{slug}"' if anchor_prefix else f' id="{slug}"'
            out.append(f"<h{level}{anchor}>{_md_inline(text)}</h{level}>")
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^-{3,}\s*$", line) or re.match(r"^_{3,}\s*$", line):
            out.append("<hr>")
            i += 1
            continue

        # Blockquote
        if re.match(r"^\s*>\s?", line):
            html, consumed = _md_parse_blockquote(lines, i)
            out.append(html)
            i += consumed
            continue

        # GFM pipe table — header row + separator row
        if (
            "|" in line
            and i + 1 < len(lines)
            and re.match(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$", lines[i + 1])
        ):
            tbl, consumed = _md_parse_table(lines, i)
            out.append(tbl)
            i += consumed
            continue

        # Unordered list
        if re.match(r"^\s*[-*]\s+", line):
            lst, consumed = _md_parse_list(lines, i, ordered=False)
            out.append(lst)
            i += consumed
            continue

        # Ordered list
        if re.match(r"^\s*\d+\.\s+", line):
            lst, consumed = _md_parse_list(lines, i, ordered=True)
            out.append(lst)
            i += consumed
            continue

        # Blank line
        if not stripped:
            i += 1
            continue

        # Paragraph — gather contiguous non-block lines
        para = [line]
        i += 1
        while i < len(lines):
            nxt = lines[i]
            if not nxt.strip():
                break
            if re.match(r"^(#{1,6}\s|[-*]\s|\d+\.\s|>\s?|```|-{3,}\s*$|_{3,}\s*$)", nxt):
                break
            if "|" in nxt and i + 1 < len(lines) and re.match(
                r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$",
                lines[i + 1] if i + 1 < len(lines) else "",
            ):
                break
            para.append(nxt)
            i += 1
        out.append(f"<p>{_md_inline(' '.join(s.strip() for s in para))}</p>")

    return "\n".join(out)


def render_markdown_tab(path: Path, anchor_prefix: str) -> str:
    """Read a markdown artifact and return the HTML for its tab pane.

    Wraps the rendered content in <div class="md-content">. If the file is
    missing or empty, returns a small placeholder so the composite still builds
    (the caller decides whether to emit the tab at all). Fidelity: the whole
    file is rendered — nothing is summarized or dropped.
    """
    if not path.exists():
        return (
            '<div class="md-content"><p style="color:#8892a4;font-style:italic;">'
            f"Source file <code>{path.name}</code> not found in run directory."
            "</p></div>"
        )
    md_text = path.read_text(encoding="utf-8")
    if not md_text.strip():
        return (
            '<div class="md-content"><p style="color:#8892a4;font-style:italic;">'
            f"Source file <code>{path.name}</code> is empty."
            "</p></div>"
        )
    body = render_markdown_to_html(md_text, anchor_prefix=anchor_prefix)
    return f'<div class="md-content">{body}</div>'


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic delta-cell colouring (Follow-ups tab)
# ─────────────────────────────────────────────────────────────────────────────

_TD_RE = re.compile(r"<td\b([^>]*)>(.*?)</td>", re.DOTALL | re.IGNORECASE)
_STRIP_TAGS_RE = re.compile(r"<[^>]+>")
# A "signed delta" cell: visible text begins (after an optional "(") with an
# explicit +/− sign followed by a digit (optionally a currency symbol first).
# Covers −3.13pp, +0.6pp, -15%, +98%, +$111.3K, (−$708.8K). A plain count
# ("6,447"), a level ("21.6%"), or an em-dash placeholder ("—") has no leading
# sign and is left untouched.
_SIGNED_DELTA_RE = re.compile(r"^\(?\s*([+\-−–])\s*\$?\d")
_HAS_COLOR_CLASS_RE = re.compile(r"\b(neg|pos|flat)\b")


def autocolor_delta_cells(html: str) -> str:
    """Add `.pos`/`.neg` to table cells whose value is a signed delta.

    Deterministic, sign-based, scoped to the caller (used for the Follow-ups
    tab). Green for a leading `+`, red for a leading `-`/`−`/`–`. **Author
    intent wins:** a `<td>` that already carries a `neg`/`pos`/`flat` class is
    left exactly as written — so semantic cells the parser can't infer (e.g. a
    *positive* "lost checkouts" count the author marked `.neg`) are preserved.
    Cells without a leading sign (counts, levels, "—") are never touched.
    """

    def repl(m: "re.Match[str]") -> str:
        attrs, inner = m.group(1), m.group(2)
        cls_m = re.search(r'class\s*=\s*"([^"]*)"', attrs, re.IGNORECASE)
        existing = cls_m.group(1) if cls_m else ""
        if _HAS_COLOR_CLASS_RE.search(existing):
            return m.group(0)  # respect an author-set colour
        text = _STRIP_TAGS_RE.sub("", inner).strip()
        dm = _SIGNED_DELTA_RE.match(text)
        if not dm:
            return m.group(0)
        color = "pos" if dm.group(1) == "+" else "neg"
        if cls_m:
            merged = (existing + " " + color).strip()
            new_attrs = attrs[: cls_m.start(1)] + merged + attrs[cls_m.end(1) :]
        else:
            new_attrs = f'{attrs} class="{color}"'
        return f"<td{new_attrs}>{inner}</td>"

    return _TD_RE.sub(repl, html)


# ─────────────────────────────────────────────────────────────────────────────
# CVR-RCA report.html extraction
# ─────────────────────────────────────────────────────────────────────────────

def _extract_div_by_id(html: str, div_id: str) -> str | None:
    """Return the inner HTML of <div id="div_id" ...>...</div>, or None.

    Depth-aware: counts nested <div> opens/closes so we capture the full pane
    even though it contains many nested divs. Regex alone can't balance tags,
    so we find the opening tag then walk the string counting div depth.
    """
    m = re.search(rf'<div\b[^>]*\bid="{re.escape(div_id)}"[^>]*>', html)
    if not m:
        return None
    start = m.end()
    depth = 1
    pos = start
    div_open = re.compile(r"<div\b", re.IGNORECASE)
    div_close = re.compile(r"</div>", re.IGNORECASE)
    while depth > 0 and pos < len(html):
        next_open = div_open.search(html, pos)
        next_close = div_close.search(html, pos)
        if next_close is None:
            break  # malformed; bail
        if next_open is not None and next_open.start() < next_close.start():
            depth += 1
            pos = next_open.end()
        else:
            depth -= 1
            if depth == 0:
                return html[start:next_close.start()]
            pos = next_close.end()
    return html[start:] if depth > 0 else None


def _extract_plotly_scripts(html: str) -> str:
    """Return all <script>...</script> blocks that reference Plotly.

    CVR-RCA renders charts via Plotly.newPlot(...) scripts at the end of <body>,
    outside any tab pane. The composite must re-inject these so the charts in
    the CVR-RCA tab still render. We keep only scripts that mention 'Plotly' to
    avoid pulling in unrelated inline scripts.
    """
    scripts = re.findall(r"<script\b[^>]*>.*?</script>", html, flags=re.DOTALL | re.IGNORECASE)
    plotly = [s for s in scripts if "Plotly" in s or "plotly" in s]
    return "\n".join(plotly)


def extract_cvr_rca_tab(html: str) -> tuple[str, str]:
    """Extract CVR-RCA's CVR content + its Plotly scripts from a report.html.

    Returns (body_html, scripts_html).

    Contract — depends on cvr-rca's tab framework (visual_kit.md "Tabbed report
    structure"). CVR-RCA's report has one of two shapes:
      • 2-tab: <div id="tab-cvr-rca"> (CVR content) + <div id="tab-perfaudit">.
        We take ONLY tab-cvr-rca — the master renders perf-audit as its own
        peer tab, so pulling CVR-RCA's internal perf-audit tab would duplicate.
      • single-tab flat: no tab wrappers; content sits directly in
        <div class="container">. We take the container's inner HTML.

    Plotly scripts are extracted separately (they live outside the pane) and
    returned for re-injection before </body> in the composite.
    """
    body = _extract_div_by_id(html, "tab-cvr-rca")
    if body is None:
        # single-tab flat report — take the .container inner HTML
        m = re.search(r'<div\b[^>]*\bclass="container"[^>]*>', html)
        if m:
            body = _extract_div_by_id_from_match(html, m)
        else:
            # last resort: whole <body> inner
            bm = re.search(r"<body\b[^>]*>(.*)</body>", html, flags=re.DOTALL | re.IGNORECASE)
            body = bm.group(1) if bm else html
    scripts = _extract_plotly_scripts(html)
    return body, scripts


def extract_and_scope_cvr_style(html: str, scope: str) -> str:
    """Pull the CVR-RCA report's own <style> block and scope every rule to `scope`.

    The standalone cvr_rca_report.html ships a complete, self-contained <style>
    that defines every class its body uses (.metric-grid, .card, .shapley-seg,
    .action-card, etc.). The composite injects ce-rca's shared visual_kit CSS for
    its chrome, which has drifted from cvr-rca's and lacks many of those classes —
    so the extracted CVR pane renders unstyled. Rather than chase drift class by
    class, we carry CVR-RCA's own stylesheet verbatim, prefixing every selector
    with `scope` (e.g. `#tab-cvr-rca`). The ID prefix makes these rules both
    self-sufficient (they fully style the pane) and inert outside it (higher
    specificity wins inside the pane; zero reach outside), so the other tabs and
    the composite chrome are untouched.
    """
    m = re.search(r"<style>(.*?)</style>", html, flags=re.DOTALL | re.IGNORECASE)
    if not m:
        return ""
    return _scope_css(m.group(1), scope)


def _scope_css(css: str, scope: str) -> str:
    """Prefix every selector in `css` with `scope`. Handles @media blocks
    (recursively), comma-separated selector lists, the universal reset, and
    :root/html/body (mapped to the scope element itself so CSS custom properties
    and base styles land on the pane, which is the root of the embedded content).
    """
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)  # strip comments
    out = []
    i, n = 0, len(css)
    while i < n:
        brace = css.find("{", i)
        if brace == -1:
            break
        prelude = css[i:brace].strip()
        if prelude.startswith("@"):
            # At-rule with a block (e.g. @media): recurse on the inner rules.
            depth, j = 0, brace
            while j < n:
                if css[j] == "{":
                    depth += 1
                elif css[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            inner = css[brace + 1:j]
            out.append(f"{prelude} {{\n{_scope_css(inner, scope)}\n}}")
            i = j + 1
        else:
            close = css.find("}", brace)
            if close == -1:
                break
            decls = css[brace + 1:close].strip()
            out.append(f"{_scope_selectors(prelude, scope)} {{ {decls} }}")
            i = close + 1
    return "\n".join(out)


def _scope_selectors(selector_list: str, scope: str) -> str:
    parts = [s.strip() for s in selector_list.split(",") if s.strip()]
    return ", ".join(_scope_one(s, scope) for s in parts)


def _scope_one(sel: str, scope: str) -> str:
    # :root / html / body map to the scope element itself so variables defined on
    # :root and base body styles apply to the pane (the embedded content's root).
    if sel in (":root", "html", "body"):
        return scope
    sel = re.sub(r"^(?:html|body)\b", scope, sel)  # body.x → scope.x
    if sel.startswith(scope):
        return sel
    return f"{scope} {sel}"


def _extract_div_by_id_from_match(html: str, open_match) -> str:
    """Depth-aware inner-HTML extraction starting from an already-found opening <div>."""
    start = open_match.end()
    depth = 1
    pos = start
    div_open = re.compile(r"<div\b", re.IGNORECASE)
    div_close = re.compile(r"</div>", re.IGNORECASE)
    while depth > 0 and pos < len(html):
        next_open = div_open.search(html, pos)
        next_close = div_close.search(html, pos)
        if next_close is None:
            break
        if next_open is not None and next_open.start() < next_close.start():
            depth += 1
            pos = next_open.end()
        else:
            depth -= 1
            if depth == 0:
                return html[start:next_close.start()]
            pos = next_close.end()
    return html[start:]
