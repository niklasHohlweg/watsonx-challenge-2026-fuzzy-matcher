#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# release.sh — build FuzzyMatcher locally and publish to GitHub Releases
#
# Usage:
#   chmod +x release.sh
#   ./release.sh
#
# Prerequisites:
#   - Python venv already set up (.venv/)
#   - GitHub CLI installed (https://cli.github.com) and authenticated:
#       gh auth login
#   OR set GITHUB_TOKEN env var and the script uses curl instead.
#
# The script will:
#   1. Run the test suite (aborts on failure)
#   2. Build FuzzyMatcher.app + FuzzyMatcher-macOS.dmg via PyInstaller
#   3. Delete the existing "latest" GitHub release (if any)
#   4. Create a new "latest" release and upload the .dmg
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV="$SCRIPT_DIR/.venv"
PYTHON="$VENV/bin/python"
PIP="$VENV/bin/pip"
PYINSTALLER="$VENV/bin/pyinstaller"
PYTEST="$VENV/bin/python -m pytest"

DMG_NAME="FuzzyMatcher-macOS.dmg"
DMG_PATH="$SCRIPT_DIR/dist/$DMG_NAME"
APP_PATH="$SCRIPT_DIR/dist/FuzzyMatcher.app"

RELEASE_TAG="latest"
RELEASE_TITLE="Fuzzy Account Matcher — latest build"
RELEASE_NOTES="Built locally on $(date '+%Y-%m-%d %H:%M') from $(git rev-parse --short HEAD 2>/dev/null || echo 'unknown commit').

## Download
- **macOS**: Open the .dmg, drag the app to Applications, right-click → Open on first launch."

# ── Colour helpers ────────────────────────────────────────────────────────────
green()  { echo -e "\033[0;32m$*\033[0m"; }
red()    { echo -e "\033[0;31m$*\033[0m"; }
yellow() { echo -e "\033[0;33m$*\033[0m"; }
step()   { echo; echo -e "\033[1;34m▶ $*\033[0m"; }

# ── 0. Preflight checks ───────────────────────────────────────────────────────
step "Preflight checks"

if [[ ! -d "$VENV" ]]; then
    red "Virtual environment not found at .venv/"
    echo "Create it first:"
    echo "  python3 -m venv .venv"
    echo "  .venv/bin/pip install PySide6 openpyxl pandas rapidfuzz PyInstaller pytest"
    exit 1
fi

if ! command -v gh &>/dev/null && [[ -z "${GITHUB_TOKEN:-}" ]]; then
    red "Neither 'gh' CLI nor GITHUB_TOKEN found."
    echo "Install gh CLI:  brew install gh  then run:  gh auth login"
    echo "Or set:          export GITHUB_TOKEN=ghp_..."
    exit 1
fi

green "Preflight OK"

# ── 1. Tests ──────────────────────────────────────────────────────────────────
step "Running tests"
$PYTEST tests/ -v --tb=short
green "All tests passed"

# ── 2. Install PyInstaller if missing ─────────────────────────────────────────
if [[ ! -f "$PYINSTALLER" ]]; then
    step "Installing PyInstaller"
    $PIP install --quiet "PyInstaller>=6.6"
fi

# ── 3. Build ──────────────────────────────────────────────────────────────────
step "Building with PyInstaller"
$PYINSTALLER fuzzy_matcher.spec --noconfirm
green "Build complete: $APP_PATH"

# ── 4. Package into .dmg ──────────────────────────────────────────────────────
step "Packaging into .dmg"
rm -f "$DMG_PATH"
hdiutil create \
    -volname "Fuzzy Account Matcher" \
    -srcfolder "$APP_PATH" \
    -ov -format UDZO \
    "$DMG_PATH"
green "DMG ready: $DMG_PATH ($(du -sh "$DMG_PATH" | cut -f1))"

# ── 5. Publish to GitHub Releases ─────────────────────────────────────────────
step "Publishing to GitHub Releases (tag: $RELEASE_TAG)"

if command -v gh &>/dev/null; then
    # ── Using gh CLI (recommended) ────────────────────────────────────────────
    yellow "Using gh CLI..."

    # Delete existing release + tag (ignore errors if they don't exist)
    gh release delete "$RELEASE_TAG" --yes 2>/dev/null || true
    git push origin ":refs/tags/$RELEASE_TAG" 2>/dev/null || true

    gh release create "$RELEASE_TAG" \
        --title "$RELEASE_TITLE" \
        --notes "$RELEASE_NOTES" \
        --prerelease \
        "$DMG_PATH"

else
    # ── Fallback: plain curl + GITHUB_TOKEN ───────────────────────────────────
    yellow "Using curl with GITHUB_TOKEN..."

    # Detect repo from git remote
    REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
    if [[ -z "$REMOTE_URL" ]]; then
        red "Could not detect GitHub repo from git remote."
        echo "Set GITHUB_REPO manually, e.g.:  export GITHUB_REPO=owner/repo-name"
        exit 1
    fi
    # Extract owner/repo from https or ssh remote
    REPO=$(echo "$REMOTE_URL" \
        | sed -E 's|.*github\.com[:/]||; s|\.git$||')

    API="https://api.github.com/repos/$REPO"
    AUTH="Authorization: Bearer $GITHUB_TOKEN"

    # Delete existing release
    EXISTING_ID=$(curl -s -H "$AUTH" "$API/releases/tags/$RELEASE_TAG" \
        | grep '"id"' | head -1 | grep -o '[0-9]*')
    if [[ -n "$EXISTING_ID" ]]; then
        curl -s -X DELETE -H "$AUTH" "$API/releases/$EXISTING_ID" >/dev/null
    fi
    # Delete existing tag
    curl -s -X DELETE -H "$AUTH" "$API/git/refs/tags/$RELEASE_TAG" >/dev/null || true

    # Create release
    RELEASE_JSON=$(curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
        "$API/releases" \
        -d "{
            \"tag_name\": \"$RELEASE_TAG\",
            \"name\": \"$RELEASE_TITLE\",
            \"body\": $(echo "$RELEASE_NOTES" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'),
            \"prerelease\": true
        }")

    UPLOAD_URL=$(echo "$RELEASE_JSON" \
        | python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["upload_url"])' \
        | sed 's/{.*//')

    if [[ -z "$UPLOAD_URL" ]]; then
        red "Failed to create release. Response:"
        echo "$RELEASE_JSON"
        exit 1
    fi

    # Upload asset
    curl -s -X POST \
        -H "$AUTH" \
        -H "Content-Type: application/octet-stream" \
        --data-binary @"$DMG_PATH" \
        "${UPLOAD_URL}?name=$DMG_NAME" >/dev/null
fi

green "Release published!"
echo
echo "  Download at:  https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo '<your-repo>')/releases/tag/$RELEASE_TAG"
