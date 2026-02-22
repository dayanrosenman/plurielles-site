# Plurielles Site — Claude Code Context

## Project Overview
Static site for *Plurielles*, a French Jewish cultural review magazine. Built with `build.py` (Python), hosted on GitHub Pages. Source repo: `dayanrosenman/plurielles-site`.

## Key Paths
- **Site source/output**: `/Users/david/ClaudeCode/plurielles-site/` (git repo, also the output dir)
- **Build script**: `/Users/david/ClaudeCode/plurielles-site/build.py`
- **Article PDFs (issues 7-23)**: `/Users/david/CLaudeCode/plurielles/Articles Plurielles 7-23/Plurielles de 7 à 23 /Plurielles {N}/` (note trailing space and NFD-encoded `à` in path)
- **Official TOC (issues 7-22)**: `/Users/david/CLaudeCode/plurielles/PLURIELLES/PL23 Sommaires 7-22.docx`
- **InDesign sources (issues 17-24)**: `/Users/david/CLaudeCode/plurielles/PLURIELLES/Indesign PL/`
- **Issue 23 DOCX articles**: `/Users/david/CLaudeCode/plurielles/Articles Plurielles 7-23/PL23 Articles/`

## Architecture

### build.py structure
- `ISSUES` dict (keys 1-24): metadata + article list for each issue
  - `known_articles` list order **must match Python string-sort order of PDF filenames** in the issue folder — this is how title/author gets mapped to each PDF
  - `order` list: integer indices into string-sorted `pdf_articles` list, giving printing order for sommaire display
- `extract_pdf_text(pdf_path, fix_char_spacing=False, clip_bottom=0.86)`: extracts text via PyMuPDF (fitz), clips top 11% and bottom at `clip_bottom` fraction (default 0.86) to strip running headers/footers
- Issue processing loop (lines ~2302-2380): for each issue 7-22, reads PDFs in sorted order, maps to `known_articles[i]`, builds article HTML pages
- Sommaire display: `pdf_articles` list built in sorted order, then reordered using `order` key (or editorial-first fallback if no `order` key)

### Critical constraint
`known_articles[i]` → `pdfs[i]` (where `pdfs` = Python `sorted()` of PDF filenames). The sort is **string sort**, not numeric. E.g. `pl7-102-106.pdf` sorts before `pl7-11-17.pdf` because `"1"<"1"` then `"0"<"1"`.

## Current State (as of session 2026-02-21)

### All completed and deployed
- All issues 7-22 have complete article lists in `ISSUES` dict (15-32 articles per issue)
- All issues 7-22 have `order` list in `ISSUES` dict for printing-order sommaire display
- `clip_bottom` parameter added to `extract_pdf_text`; uses 0.92 for issues 12, 16, 22 (vs 0.86 default)
- Two misnamed PDFs fixed: `pl13.4-5pdf` → `pl13.4-5.pdf`, `pl14-126-134pdf` → `pl14-126-134.pdf`
- Prev/next article navigation uses print order (from `order` key) not filename sort order
- Improved footnote detection: `_FN_NUM_PREFIX` accepts "N." and "N " formats; `_NOTES_HEADER` strips section headers; per-page footnote renumbering via `_add_footnotes`
- All changes committed and pushed to GitHub Pages

### Footer y-positions (do not change clip defaults without checking)
- Issue 7: footer at **87%** — use 0.86 clip, DO NOT extend
- Issue 12: footer at **92%**, content to 89% — use 0.92
- Issue 16: footer at **96%**, content to 92% — use 0.92
- Issue 22: footer at **93%**, content to 90% — use 0.92

### Known limitations / possible future work
- Issues 1-6 do not have full article lists (no individual PDFs, only whole-issue PDF)
- Issues 23-24 handled separately: 23 via DOCX articles, 24 via DOCX sections

## How to Run
```bash
cd /Users/david/ClaudeCode/plurielles-site
python build.py        # rebuilds site
python3 -m http.server 8080  # preview at localhost:8080
git add -A && git commit -m "..." && git push  # deploy
```

## Dependencies
- `fitz` (PyMuPDF) — PDF extraction
- `python-docx` — DOCX reading
- Standard library only otherwise

## Notes on specific issues
- **Issue 13**: PDFs use dots not dashes: `pl13.NNN-NNN.pdf` (not `pl13-NNN-NNN.pdf`)
- **Issue 14**: `pl14-126-134.pdf` was previously missing (renamed from typo `pl14-126-134pdf`)
- **Issues 9, 10, 12, 22**: Use `fix_char_spacing=True` in extraction (older typography with char-by-char typesetting)
- **Issue 17 folder**: Contains 24 PDFs split across PL17 proper (8 articles) and PL18 "retour" articles (16). Both are stored there.
- **Issue 18 folder**: Contains PL18's second thematic set (28 articles, on histoire/mémoire theme)
