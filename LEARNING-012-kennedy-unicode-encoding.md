# LEARNING-012: Unicode Encoding — Avoiding Double-Encoding Corruption

**Date:** March 18, 2026
**Issue:** Kennedy's Telegram messages had garbled characters like `ÃÂ¢ÃÂÃÂ` in divider lines
**Root Cause:** Double-encoding corruption (UTF-8 bytes decoded as Latin-1, re-encoded as UTF-8)
**Status:** FIXED - All instances replaced with correct em dashes (—) and en dashes (–)

---

## What Happened

Kennedy's divider lines and em dashes appeared as mojibake:
```
Kennedy Status Report
ÃÂ¢ÃÂÃÂÃÂ¢ÃÂÃÂÃÂ¢ÃÂÃÂÃÂ¢ÃÂÃÂÃÂ¢ÃÂÃÂÃÂ¢ÃÂÃÂÃÂ¢ÃÂÃÂ

Should have been:
Kennedy Status Report
—–—–—–—–—–—–—–—–—–—–—–—–—–—–—–—–—–—–—–
```

The Kennedy log entry "Pending review already sent to David ÃÂ¢ÃÂÃÂ waiting for response" should read:
"Pending review already sent to David — waiting for response"

---

## Root Cause: Double-Encoding Corruption

### The Byte Trail

1. **Correct UTF-8 encoding of em dash (—):** `E2 80 94` (3 bytes)
2. **Byte 0xE2 mistakenly decoded as Latin-1:** Becomes character U+00E2 (â)
3. **0xE2 re-encoded as UTF-8:** Becomes bytes `C3 82` (2 bytes)
4. **Repeat for 0x80 and 0x94:** Creates double-encoded sequence

**Example:**
- Original: UTF-8 em dash = `E2 80 94`
- Mishandled as Latin-1 = `E2` → U+00E2, `80` → U+0080, `94` → U+0094
- Re-encoded to UTF-8 = `C3 82 C2 80 C2 94` (6 bytes for what should be 3)
- Displayed in UTF-8 viewer = `Ã‚€"` (mojibake)

---

## Why This Happened

This was **historical corruption** in the Kennedy source file, not a runtime encoding issue:

1. Kennedy's code correctly uses `encoding="utf-8"` in all file operations:
   - `pathlib.Path.read_text(encoding="utf-8")`
   - `open(..., encoding="utf-8")`
   - `json.dumps()` and `json.loads()`

2. The Kennedy context loader correctly specifies UTF-8 everywhere.

3. The Kennedy learning logger correctly specifies UTF-8 everywhere.

4. **The problem:** The source file itself (`agents/kennedy/kennedy.py`) had pre-corrupted em dash literals in string constants. When read as UTF-8, Python correctly decoded the broken bytes as mojibake characters.

---

## The Fix

**Applied:** Commit 67898ac
**Changes:** Replaced all 1101 broken em dash patterns and 57 broken en dash patterns with correct Unicode characters.

```python
# Before (corrupted source):
f"ÃÂ¢ÃÂÃÂÃÂ¢ÃÂÃÂÃÂ¢ÃÂÃÂÃÂ¢ÃÂÃÂÃÂ¢ÃÂÃÂ\n"  # Wrong bytes in source

# After (fixed source):
f"—–—–—–—–—–—–—–—–—–—–—–—–—–—–\n"  # Correct Unicode characters
```

**File Impact:**
- File size: 36,879 → 29,001 characters (7,878 bytes of double-encoding removed)
- Functionality: Unchanged
- Display: Now correct in all contexts (Telegram, logs, etc.)

---

## Lessons for All Agents

### 1. Always Specify Encoding Explicitly

When reading or writing files with non-ASCII characters:

```python
# CORRECT - explicit UTF-8
content = path.read_text(encoding='utf-8')
path.write_text(content, encoding='utf-8')

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# WRONG - relies on system default (may be ASCII or Latin-1 on some systems)
content = path.read_text()  # ← Can fail silently on non-ASCII
```

### 2. Check Your Editor Settings

Use an editor that:
- Defaults to UTF-8 encoding (VS Code, PyCharm, Sublime Text 3+)
- Shows file encoding in status bar
- Can detect and convert between encodings

Do NOT use editors that default to Latin-1 or system locale encoding for code files.

### 3. Validate Non-ASCII Content

If you include non-ASCII characters in source code (em dashes, special symbols):

```python
# Verify file encoding at the top of the file:
# -*- coding: utf-8 -*-

# Or Python 3 (default UTF-8):
"""File with em dashes — like this."""

# Test it loads correctly:
import sys
text = "Test em dash — here"
assert "—" in text, "Em dash corruption detected!"
```

### 4. Prevent Double-Encoding at the Source

**Signs of double-encoding:**
- Characters like `ÃÂ`, `â€`, `Â¢` appearing in output
- File size larger than expected for the text
- Correct UTF-8 display in some tools, mojibake in others

**How it happens:**
1. File created in editor with wrong encoding setting
2. Or: File handled by script with wrong encoding assumption
3. Or: File transmitted over non-UTF-8 protocol

**Prevention:**
- Version control: Always commit as UTF-8
- APIs: Always send `Content-Type: application/json; charset=utf-8`
- File operations: Explicit `encoding='utf-8'` always
- Testing: Assert non-ASCII characters survive round-trip

### 5. Testing Non-ASCII Strings

Add to your tests:

```python
def test_unicode_preservation():
    """Verify Unicode characters survive encode/decode."""
    test_strings = {
        "em_dash": "Alert — something happened",
        "copyright": "© 2026",
        "math": "2 × 3 = 6",
    }

    for name, text in test_strings.items():
        # Test file write/read
        path.write_text(text, encoding='utf-8')
        loaded = path.read_text(encoding='utf-8')
        assert loaded == text, f"{name} corrupted: {repr(loaded)}"

        # Test JSON serialization
        import json
        serialized = json.dumps(text)
        deserialized = json.loads(serialized)
        assert deserialized == text, f"{name} JSON corrupted"
```

---

## Impact on Kennedy's Operations

**Before Fix:**
- Telegram messages showed: `ÃÂ¢ÃÂÃÂ waiting for response`
- Logs had mojibake divider lines
- User experience: Unprofessional, hard to parse

**After Fix:**
- Telegram messages show: `— waiting for response` (correct em dash)
- Logs have clean divider lines: `—–—–—–—–—–`
- User experience: Professional, easy to read

---

## Files Affected

- `agents/kennedy/kennedy.py` - Fixed (1101 em dashes + 57 en dashes corrected)
- `agents/kennedy/brain.md` - Already correct (no double-encoding)
- `agents/kennedy/kennedy_context_loader.py` - Already correct (only reads UTF-8)
- `agents/kennedy/kennedy_learning_logger.py` - Already correct (only writes UTF-8)

---

## For Other Agents: Apply This Knowledge

If you:
- Generate formatted messages with special characters
- Store dividers or decorative elements in strings
- Send output to Telegram, email, or APIs

Then:
1. Use explicit UTF-8 encoding in all file operations
2. Test non-ASCII round-trip preservation
3. Use proper Unicode characters, not mojibake replacements
4. Never hand-edit strings with UTF-8 in editors set to Latin-1

---

## Related Issues

- Issue: "Kennedy's Telegram messages have garbled characters"
- Reporter: David (via manual inspection of Telegram logs)
- Severity: Medium (functional but unprofessional)
- Category: Data quality / Character encoding

---

## Commands to Prevent This

```bash
# Check file encoding
file agents/kennedy/kennedy.py
# Should show: UTF-8 text

# View hex dump of specific character
hexdump -C agents/kennedy/kennedy.py | grep -A 2 -B 2 "e2 80 94"

# Validate UTF-8
python3 -c "
with open('agents/kennedy/kennedy.py', 'r', encoding='utf-8') as f:
    content = f.read()
    print(f'File size: {len(content)} chars')
    print(f'Em dashes: {content.count(\"—\")}')
    print(f'Broken patterns: {content.count(\"ÃÂ¢ÃÂÃÂ\")}')
"
```

---

**Status:** RESOLVED
**Fixed by:** Unicode encoding fix script (commit 67898ac)
**Verified:** All em dashes and dividers now display correctly
