import requests
from providers import _common as C

NAME = "TikTok"
ACCOUNTS = C.ROOT / "accounts" / "tiktok.json"
LOG      = C.ROOT / "logs" / "tiktok.jsonl"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

BASE = {
    "aid": "1988", "app_name": "tiktok_web", "app_language": "en",
    "browser_language": "en-US", "browser_name": "Mozilla", "browser_online": "true",
    "browser_platform": "Win32", "channel": "tiktok_web", "cookie_enabled": "true",
    "device_platform": "web_pc", "focus_state": "true", "is_fullscreen": "false",
    "is_page_visible": "true", "os": "windows", "priority_region": "US",
    "region": "US", "screen_height": "1080", "screen_width": "1920",
    "tz_name": "UTC", "webcast_language": "en",
}

# קודי סיבה פנימיים של טיקטוק. אפשר להוסיף עוד כדי לירות כמה דיווחים מאותו חשבון
REASONS = ["9009"]

COOKIE_KEYS = ("sessionid", "sessionid_ss", "sid_tt", "tt_csrf_token", "uid_tt", "passport_csrf_token")

def _accounts():
    return {k: v for k, v in C.read_json(ACCOUNTS).items() if not k.startswith("_")}

def _cookies(entry):
    if "cookies" in entry:
        return entry["cookies"]
    return {k: v for k, v in entry.items() if k in COOKIE_KEYS}

def _get(endpoint, params, cookies):
    r = requests.get(
        f"https://www.tiktok.com/{endpoint}",
        params={**BASE, **params},
        headers={"user-agent": UA, "referer": "https://www.tiktok.com/", "accept": "*/*"},
        cookies=cookies, timeout=30,
    )
    r.raise_for_status()
    return r.json()

def show_accounts():
    acc = _accounts()
    print(f"\n{len(acc)} רשומות:")
    for name, entry in acc.items():
        print(f"  {name}  sessionid={'כן' if _cookies(entry).get('sessionid') else 'חסר'}")

def login_all():
    print("\nטיקטוק מאמת לפי קוקי. בודק שכל הקוקיז חיים:\n")
    acc = _accounts()
    for i, (name, entry) in enumerate(acc.items(), 1):
        ck = _cookies(entry)
        if not ck.get("sessionid"):
            print(f"  [{i}/{len(acc)}] {name}  ! חסר sessionid")
            continue
        try:
            me = _get("passport/web/account/info/", {}, ck).get("data", {})
            print(f"  [{i}/{len(acc)}] {name}  OK uid={me.get('user_id')}")
        except Exception as e:
            print(f"  [{i}/{len(acc)}] {name}  X {e}")
        C.pace(3, 8)

def report_all(target):
    acc = _accounts()
    done = {r["account"] for r in C.read_log(LOG) if r.get("ok")}
    todo = [k for k in acc if k not in done]
    print(f"\nיעד: @{target} | בתור: {len(todo)}\n")

    for i, name in enumerate(todo, 1):
        ck = _cookies(acc[name])
        try:
            user = _get("api/user/detail/", {"uniqueId": target}, ck).get("userInfo", {}).get("user")
            if not user:
                raise RuntimeError("המשתמש לא נמצא")
            reporter = _get("passport/web/account/info/", {}, ck).get("data", {}).get("user_id")

            for reason in REASONS:
                _get("aweme/v2/aweme/feedback/", {
                    "secUid": user["secUid"], "nickname": user["nickname"],
                    "object_id": user["id"], "owner_id": user["id"],
                    "target": user["id"], "reporter_id": reporter,
                    "reason": reason, "report_type": "user",
                }, ck)

            C.append_log(LOG, {"account": name, "target": target, "ok": True})
            print(f"  [{i}/{len(todo)}] {name} -> @{target}  OK")
        except Exception as e:
            C.append_log(LOG, {"account": name, "target": target, "ok": False, "err": str(e)})
            print(f"  [{i}/{len(todo)}] {name}  X {e}")
        C.pace(3, 10)

def status():
    acc, rows = _accounts(), C.read_log(LOG)
    ok = {r["account"] for r in rows if r.get("ok")}
    print(f"\nסה\"כ: {len(acc)} | דיווחו: {len(ok)} | נשארו: {len(acc) - len(ok)}")
    left = [k for k in acc if k not in ok]
    if left:
        print("\nלא דיווחו: " + ", ".join(left))
