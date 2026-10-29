import json

from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired, LoginRequired, PleaseWaitFewMinutes

from providers import _common as C

NAME = "Instagram"
ACCOUNTS = C.ROOT / "accounts" / "instagram.json"
SESSIONS = C.ROOT / "sessions" / "instagram"
LOG      = C.ROOT / "logs" / "instagram.jsonl"
REASON   = "spam"


def _accounts():
    return {k: v for k, v in C.read_json(ACCOUNTS).items() if not k.startswith("_")}


def _reported():
    return {r["account"] for r in C.read_log(LOG) if r.get("ok")}


def show_accounts():
    acc = _accounts()
    print(f"\n{len(acc)} חשבונות טעונים:")
    for i, (u, e) in enumerate(acc.items(), 1):
        tag = "  [sessionid]" if isinstance(e, dict) and e.get("sessionid") else ""
        print(f"  {i:>2}. {u}{tag}")


def _email_choice(challenge):
    """מאתר את אפשרות המייל ברשימת שיטות האימות של אינסטגרם."""
    data = (challenge or {}).get("step_data") or {}
    for pair in data.get("choices") or []:
        try:
            label, value = str(pair[0]), pair[1]
        except (IndexError, TypeError):
            continue
        if "mail" in label.lower():
            return value
    return None


def _ask_code(username, choice):
    print()
    print("  ── נדרש קוד אימות ──")
    print("  בדוק את המייל של החשבון (גם בספאם).")
    print("  הסקריפט ממתין — אפשר גם לאשר באפליקציה, אבל לא חייב.")
    for _ in range(5):
        code = input(f"  [{username}] קוד: ").strip()
        if code:
            return code
    return None


def _client(username, entry):
    SESSIONS.mkdir(parents=True, exist_ok=True)
    password = entry.get("password") if isinstance(entry, dict) else entry
    sessionid = entry.get("sessionid") if isinstance(entry, dict) else None

    cl = Client()
    cl.delay_range = [2, 5]
    cl.set_locale("en_US")
    cl.set_timezone_offset(10800)

    sf = SESSIONS / f"{username}.json"
    if sf.exists():
        cl.set_settings(json.loads(sf.read_text(encoding="utf-8")))
    else:
        sf.write_text(json.dumps(cl.get_settings()), encoding="utf-8")

    cl.challenge_code_handler = lambda u, c: _ask_code(u, c)
    cl.totp_generator = lambda: input(f"[{username}] קוד 2FA: ").strip()

    if sessionid:
        cl.login_by_sessionid(sessionid)
        sf.write_text(json.dumps(cl.get_settings()), encoding="utf-8")
        return cl

    try:
        cl.login(username, password)
    except ChallengeRequired:
        challenge = (cl.last_json or {}).get("challenge")
        if not challenge:
            raise
        choice = _email_choice(challenge)
        print(f"\n  שיטת אימות שנבחרה: {'מייל' if choice else 'ברירת מחדל של אינסטגרם'}")
        cl.challenge_resolve(challenge, choice=choice)
        cl.login(username, password)

    sf.write_text(json.dumps(cl.get_settings()), encoding="utf-8")
    return cl


def login_all():
    acc = _accounts()
    print(f"\nמתחבר ל-{len(acc)} חשבונות...\n")
    for i, (username, entry) in enumerate(acc.items(), 1):
        try:
            _client(username, entry)
            print(f"  [{i}/{len(acc)}] {username}  OK - סשן נשמר")
        except ChallengeRequired:
            print(f"  [{i}/{len(acc)}] {username}  ! אתגר לא נפתר - המתן 15 דקות")
        except PleaseWaitFewMinutes:
            print(f"  [{i}/{len(acc)}] {username}  ~ המתן כמה דקות")
        except Exception as e:
            print(f"  [{i}/{len(acc)}] {username}  X {e}")
        C.pace()


def report_all(target):
    acc, done = _accounts(), _reported()
    todo = [u for u in acc if u not in done]
    print(f"\nיעד: @{target} | סה\"כ: {len(acc)} | כבר דיווחו: {len(done)} | בתור: {len(todo)}\n")

    target_id = None
    for i, username in enumerate(todo, 1):
        try:
            cl = _client(username, acc[username])
            if target_id is None:
                target_id = cl.user_id_from_username(target)
            ok = cl.user_report(target_id, reason=REASON)
            C.append_log(LOG, {"account": username, "target": target, "ok": bool(ok)})
            print(f"  [{i}/{len(todo)}] {username} -> @{target}  {'OK' if ok else '-'}")
        except PleaseWaitFewMinutes:
            C.append_log(LOG, {"account": username, "target": target, "ok": False, "err": "rate_limited"})
            print(f"  [{i}/{len(todo)}] {username}  ~ המתן")
        except LoginRequired:
            print(f"  [{i}/{len(todo)}] {username}  ! צריך להתחבר מחדש")
        except Exception as e:
            C.append_log(LOG, {"account": username, "target": target, "ok": False, "err": str(e)})
            print(f"  [{i}/{len(todo)}] {username}  X {e}")
        C.pace()


def status():
    acc, rows = _accounts(), C.read_log(LOG)
    ok = {r["account"] for r in rows if r.get("ok")}
    print(f"\nסה\"כ: {len(acc)} | דיווחו: {len(ok)} | נשארו: {len(acc) - len(ok)}")
    left = [u for u in acc if u not in ok]
    if left:
        print("\nלא דיווחו: " + ", ".join(left))
    fails = [r for r in rows if not r.get("ok")]
    for r in fails[-5:]:
        print(f"  כשל: {r['account']} — {r.get('err', '?')}")
EOF
