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
- `extract_pdf_text(pdf_path, fix_char_spacing=False)`: extracts text via PyMuPDF (fitz), clips top 11% and bottom 14% (currently `ph * 0.86`) to strip running headers/footers
- Issue processing loop (lines ~2302-2380): for each issue 7-22, reads PDFs in sorted order, maps to `known_articles[i]`, builds article HTML pages
- Sommaire display: `pdf_articles` list is built in sorted order, then the editorial is moved to position 0 (editorial-first logic added in last session)

### Critical constraint
`known_articles[i]` → `pdfs[i]` (where `pdfs` = Python `sorted()` of PDF filenames). The sort is **string sort**, not numeric. E.g. `pl7-102-106.pdf` sorts before `pl7-11-17.pdf` because `"1"<"1"` then `"0"<"1"`.

## Current State (as of last session)

### Completed
- All issues 7-22 now have complete article lists in `ISSUES` dict (was previously only 6-11 articles per issue, now 15-32)
- Editorial-first reordering added to sommaire generation
- Two misnamed PDFs fixed: `pl13.4-5pdf` → `pl13.4-5.pdf`, `pl14-126-134pdf` → `pl14-126-134.pdf`
- All changes committed and pushed to GitHub

### Outstanding bugs to fix

#### 1. Issue 22 editorial text cut short (PRIORITY)
**File**: `pl22-4-7.pdf` (editorial, pages pp. 4-7)
**Symptom**: Last paragraph ends mid-sentence with garbled text ("a d l d d d") instead of "…le romancier de La statue de sel (1953), a créé des concepts majeurs comme celui de judéité, qui sert encore à décrire notre identité juive dans sa dimension intime et personnelle."
**Root cause**: The clip in `extract_pdf_text` cuts at `ph * 0.86` (y=604), but the last paragraph of page 4 runs from y=497 to y=633 (90% of page). Footer is safely at y=651 (93%). Content is being clipped 4% too early.
**Fix**: Change clip from `ph * 0.86` to `ph * 0.92` **only for issue 22** (and possibly issues 12 and 16 which also have content reaching 89-92%). Issue 7's footer is at 87% so changing the global default would break it. See implementation options below.

**Recommended fix** — add a `clip_bottom` parameter to `extract_pdf_text`:
```python
# In extract_pdf_text signature:
def extract_pdf_text(pdf_path, fix_char_spacing=False, clip_bottom=0.86):
    ...
    clip = fitz.Rect(0, ph * 0.11, pw, ph * clip_bottom)

# In the issue processing loop (~line 2319):
clip_bottom = 0.92 if n in {12, 16, 22} else 0.86
pages = extract_pdf_text(pdf, fix_char_spacing=(n in {9, 10, 12, 22}), clip_bottom=clip_bottom)
```

Footer y-positions measured across issues:
- Issue 7: footer at **87%** — current 86% clip is correct, DO NOT extend
- Issue 12: footer at **92%**, content to 89%
- Issue 16: footer at **96%**, content to 92%
- Issue 22: footer at **93%**, content to 90%

#### 2. Article display order should follow original printing order (PRIORITY)
**Symptom**: Articles are displayed in Python string-sort order of filenames, not the order they appear in the printed magazine.
**Example (issue 22)**: Currently shows `pl22-105-116` first (Henri Raczymow…), but the printed sommaire starts with the editorial, then Danny Trom, François Rachline, Emmanuel Levinas, Brigitte Stora, etc.
**Source of truth**: `/Users/david/CLaudeCode/plurielles/PLURIELLES/PL23 Sommaires 7-22.docx` has the official TOC for all issues 7-22 in printing order.

**Approach**: The `known_articles` list in ISSUES dict must stay in **string-sort order** (for the `known_articles[i]` → `pdfs[i]` mapping). But we can add a separate `display_order` list per issue that maps string-sorted index to display position.

**Simpler alternative**: Add a `sommaire_order` key to each issue in ISSUES dict, listing article titles (or slugs) in the intended display order. After building `pdf_articles` (string-sorted + editorial moved first), reorder it using `sommaire_order`.

**Even simpler**: In the ISSUES dict, add an `"order"` list of integer indices (0-based, in the string-sort array) representing the correct reading order. Then after building `pdf_articles`, reindex using these indices.

For example, issue 22 string-sort order is:
```
0: pl22-105-116  → Francine Kaufmann, L'Autre dans la vie…
1: pl22-117-129  → Guido Furci, Retour sur Philip Roth…
2: pl22-130-138  → François Ardeven, Blaise Pascal…
3: pl22-139-147  → Gérard Haddad, Lacan et ses Juifs…
4: pl22-148-181  → Simon Wuhl, Les foyers de la haine…
5: pl22-15-21    → Danny Trom, L'État-gardien…
6: pl22-182-188  → Daniel Oppenheim, Le regard…
7: pl22-22-27    → François Rachline, Juif, ou l'autre…
8: pl22-28-29    → Emmanuel Levinas, Le judaïsme et l'Autre…
9: pl22-30-39    → Brigitte Stora, L'antisémitisme…
10: pl22-4-7     → Izio Rosenman, Éditorial (already moved to front by editorial-first logic)
11: pl22-40-42   → Gérard Israël, René Cassin…
12: pl22-43-48   → Nadine Vasseur, Les nôtres…
13: pl22-49-56   → Yann Boissière, Se reconnaître…
14: pl22-57-72   → Martine Leibovici, Entre autres…
15: pl22-73-86   → Michèle Tauber, L'autre dans la littérature…
16: pl22-8-14    → Mireille Hadas-Lebel, Les juifs…
17: pl22-87-104  → Philippe Zard, Anatomie d'un embarras…
```

The sommaire doc ordering for issue 22 (printing order, sans editorial):
Mireille Hadas-Lebel (pl22-8-14), Danny Trom (pl22-15-21), François Rachline (pl22-22-27), Emmanuel Levinas (pl22-28-29), Brigitte Stora (pl22-30-39), Gérard Israël (pl22-40-42), Nadine Vasseur (pl22-43-48), Yann Boissière (pl22-49-56), Martine Leibovici (pl22-57-72), Michèle Tauber (pl22-73-86), Philippe Zard (pl22-87-104), Francine Kaufmann (pl22-105-116), Guido Furci (pl22-117-129), François Ardeven (pl22-130-138), Gérard Haddad (pl22-139-147), Simon Wuhl (pl22-148-181), Daniel Oppenheim (pl22-182-188)

So the display order (as indices into the string-sorted pdf_articles list, after editorial is at 0):
`[editorial, 16, 5, 7, 8, 9, 11, 12, 13, 14, 15, 17, 0, 1, 2, 3, 4, 6]`

The ordering data for all issues must be read from the sommaire docx.

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
