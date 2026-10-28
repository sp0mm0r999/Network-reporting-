import json
from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired, LoginRequired, PleaseWaitFewMinutes

from providers import _common as C

NAME = "Instagram"
ACCOUNTS = C.ROOT / "accounts" / "instagram.json"
SESSIONS = C.ROOT / "sessions" / "instagram"
LOG      = C.ROOT / "logs" / "instagram.jsonl"
REASON   = "spam"          # הערך היחיד שנתמך בספרייה כרגע

def _accounts():
    return {k: v for k, v in C.read_json(ACCOUNTS).items() if not k.startswith("_")}

def _reported():
    return {r["account"] for r in C.read_log(LOG) if r.get("ok")}

def show_accounts():
    acc = _accounts()
    print(f"\n{len(acc)} חשבונות טעונים:")
    for i, u in enumerate(acc, 1):
        print(f"  {i:>2}. {u}")

def _client(username, password):
    SESSIONS.mkdir(parents=True, exist_ok=True)
    cl = Client()
    cl.delay_range = [2, 5]
    cl.challenge_code_handler = lambda u, choice: input(f"[{u}] קוד אימות ({choice}): ")
    cl.totp_generator = lambda: input(f"[{username}] קוד 2FA: ")

    sf = SESSIONS / f"{username}.json"
    if sf.exists():
        cl.set_settings(json.loads(sf.read_text(encoding="utf-8")))

    cl.login(username, password)
    sf.write_text(json.dumps(cl.get_settings()), encoding="utf-8")
    return cl

def login_all():
    acc = _accounts()
    print(f"\nמתחבר ל-{len(acc)} חשבונות...\n")
    for i, (username, password) in enumerate(acc.items(), 1):
        try:
            _client(username, password)
            print(f"  [{i}/{len(acc)}] {username}  OK - סשן נשמר")
        except ChallengeRequired:
            print(f"  [{i}/{len(acc)}] {username}  ! נדרש אימות, הרץ שוב")
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
            print(f"  [{i}/{len(todo)}] {username}  ~ אינסטגרם ביקשה להמתין")
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
