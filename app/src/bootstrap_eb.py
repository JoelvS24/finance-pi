"""One-time setup: walk through the Enable Banking 90-day consent."""
from __future__ import annotations

import os

from src.enable_banking import start_auth, finish_auth


def main():
    redirect = os.environ.get("EB_REDIRECT_URL") or input("Redirect URL: ").strip()
    info = start_auth(redirect_url=redirect, valid_days=90)
    print("\nOpen this URL on the phone where Rabo Bankieren is installed:\n")
    print(f"  {info['url']}\n")
    print(f"After approving, the bank will redirect to:\n  {redirect}?code=XXXX&state=...\n")
    code = input("Paste the 'code' parameter from the redirect URL: ").strip()
    session_id = finish_auth(code)
    print(f"\n✓ Active session: {session_id}")
    print("Your Rabobank accounts have been added to the database.")


if __name__ == "__main__":
    main()
