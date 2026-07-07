# Fuzzy Account Matcher

A cross-platform desktop application for fuzzy-matching company and account names between two Excel files.

## Features

- Load two Excel files; pick any column from each for comparison
- Weighted fuzzy algorithm: Jaccard token similarity (40%) + character ratio (35%) + partial ratio (25%)
- Quality tiers: Exact / Good / Possible / No Match — colour-coded in the output
- Choose extra columns from each file to include in the export
- Multi-sheet Excel output: Summary, Matched, Unmatched
- Runs entirely in-process — no internet connection required

## Requirements

- Python 3.11 or newer
- pip

## Local Development Setup

```bash
# 1. Clone / unzip the project
cd fuzzy_matcher

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows PowerShell

# 3. Install runtime + dev dependencies
pip install -e ".[dev]"
# or, using requirements file:
pip install PySide6>=6.7 openpyxl>=3.1 pandas>=2.2 rapidfuzz>=3.9

# 4. Run the application
python main.py

# 5. Run tests
pip install pytest
pytest tests/ -v
```

## Building a Standalone Executable

### Prerequisites

```bash
pip install "PyInstaller>=6.6"
```

### macOS (produces `dist/FuzzyMatcher.app`)

```bash
cd fuzzy_matcher
pyinstaller fuzzy_matcher.spec
```

To distribute, wrap in a DMG:
```bash
hdiutil create -volname "FuzzyMatcher" -srcfolder dist/FuzzyMatcher.app \
    -ov -format UDZO dist/FuzzyMatcher.dmg
```

**Code-signing (required to suppress Gatekeeper warnings):**
```bash
# Sign the app bundle with your Apple Developer ID
codesign --deep --force --options=runtime \
    --sign "Developer ID Application: Your Name (TEAMID)" \
    dist/FuzzyMatcher.app

# Notarize (requires an App Store Connect API key)
xcrun notarytool submit dist/FuzzyMatcher.dmg \
    --apple-id you@example.com \
    --team-id TEAMID \
    --password @keychain:AC_PASSWORD \
    --wait

xcrun stapler staple dist/FuzzyMatcher.dmg
```

### Windows (produces `dist/FuzzyMatcher/FuzzyMatcher.exe`)

```cmd
cd fuzzy_matcher
pyinstaller fuzzy_matcher.spec
```

To distribute: zip the `dist/FuzzyMatcher` folder and share.

**Suppressing SmartScreen warnings** requires an EV (Extended Validation) code-signing certificate:
```cmd
signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 \
    /a dist\FuzzyMatcher\FuzzyMatcher.exe
```

## Known PyInstaller Pitfalls

| Issue | Fix |
|---|---|
| `pandas` trying to import `pyarrow` | Already excluded in `fuzzy_matcher.spec` via `excludes=["pyarrow"]` |
| PySide6 platform plugin not found | PyInstaller's PySide6 hook handles this automatically in version ≥ 6.x |
| openpyxl template files missing | The `hiddenimports` list in the spec includes `openpyxl.cell._writer` |
| macOS: app crashes on first launch | Ensure `argv_emulation=False` (already set) and test on a clean machine |

## Algorithm Details

| Signal | Weight | Purpose |
|---|---|---|
| Jaccard on normalized token sets | 40% | Handles word-order variance |
| rapidfuzz `ratio` | 35% | Character-level similarity / typo tolerance |
| rapidfuzz `partial_ratio` | 25% | Substring / abbreviation matching |

**Quality tiers:**

| Tier | Threshold |
|---|---|
| Exact | ≥ 0.97 |
| Good | ≥ 0.80 |
| Possible | ≥ 0.60 |
| No Match | < 0.60 |

**Normalization steps:** whitespace collapse → lowercase → punctuation removal → legal-entity suffix removal (GmbH, AG, Inc, Ltd, LLC, …) → stopword removal (the, and, of, …)

## Project Structure

```
fuzzy_matcher/
├── main.py              Entry point
├── ui/
│   ├── main_window.py   MainWindow + AppState wizard shell
│   ├── step1_input.py   File pickers + column dropdowns
│   ├── step2_matching.py Run button, progress bar, preview
│   └── step3_output.py  Column checkboxes + export
├── core/
│   ├── excel_reader.py  Excel → DataFrame loader
│   ├── normalizer.py    Text normalization pipeline
│   ├── scorer.py        Weighted similarity scoring
│   ├── matcher.py       Row-by-row matching orchestrator
│   └── exporter.py      Multi-sheet Excel output builder
├── models/
│   └── match_result.py  MatchResult dataclass
├── workers/
│   └── match_worker.py  QThread worker for background matching
├── tests/               pytest test suite
├── resources/icons/     App icons (.ico / .icns)
├── fuzzy_matcher.spec   PyInstaller build spec
└── pyproject.toml       Project metadata + dependencies
```
