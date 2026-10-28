#!/usr/bin/env python3
import importlib, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

def load_providers():
    found = {}
    for f in sorted((ROOT / "providers").glob("*.py")):
        if f.stem.startswith("_"):
            continue
        mod = importlib.import_module(f"providers.{f.stem}")
        if hasattr(mod, "NAME") and hasattr(mod, "report_all"):
            found[f.stem] = mod
    return found

def ask(prompt):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return "0"

def header(text):
    print("\n" + "=" * 44)
    print(text)
    print("=" * 44)

def provider_menu(key, mod):
    while True:
        header(f"{mod.NAME}")
        print("  1) התחברות לכל החשבונות")
        print("  2) דיווח על משתמש")
        print("  3) סטטוס — מי כבר דיווח")
        print("  4) הצג את החשבונות בקובץ")
        print("  0) חזרה")
        choice = ask("בחירה: ")

        if choice == "1":
            mod.login_all()
        elif choice == "2":
            target = ask("שם משתמש לדיווח (בלי @): ")
            if target:
                mod.report_all(target)
        elif choice == "3":
            mod.status()
        elif choice == "4":
            mod.show_accounts()
        elif choice == "0":
            return

def main():
    while True:
        providers = load_providers()
        if not providers:
            print("לא נמצאו ספקים בתיקיית providers/")
            return
        header("מערכת דיווח")
        keys = list(providers)
        for i, k in enumerate(keys, 1):
            print(f"  {i}) {providers[k].NAME}")
        print("  0) יציאה")

        c = ask("בחירה: ")
        if c == "0":
            return
        if c.isdigit() and 1 <= int(c) <= len(keys):
            provider_menu(keys[int(c) - 1], providers[keys[int(c) - 1]])

if __name__ == "__main__":
    main()
