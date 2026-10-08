"""
auth.py - Active Directory authentication + user sync for the IT Assets system.

Flow:
  1. authenticate_ad(username, password) -> binds to AD, returns user info or None
  2. sync_user(username, ad_info)         -> inserts or updates Users row, returns row
  3. authenticate_and_sync(...)           -> convenience wrapper for the /login endpoint
"""

import os
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.core.exceptions import LDAPBindError, LDAPException

from database import get_db_cursor

load_dotenv()

AD_SERVER  = os.getenv("AD_SERVER",  "HNL-DC.hnl.tv")
AD_DOMAIN  = os.getenv("AD_DOMAIN",  "hnl.tv")
AD_BASE_DN = os.getenv("AD_BASE_DN", "DC=hnl,DC=tv")


# ---------------------------------------------------------------------------
# 1. LDAP authentication
# ---------------------------------------------------------------------------
def authenticate_ad(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Bind to Active Directory with the given credentials.
    Returns a dict with user attributes on success, or None on failure.
    """
    if not username or not password:
        return None

    server = Server(AD_SERVER, get_info=ALL)

    try:
        conn = Connection(
            server,
            user=f"{username}@{AD_DOMAIN}",
            password=password,
            auto_bind=True,
        )
    except LDAPBindError:
        return None
    except LDAPException as exc:
        print(f"[auth] LDAP error for {username}: {exc}")
        return None

    try:
        conn.search(
            search_base=AD_BASE_DN,
            search_filter=f"(&(objectClass=user)(sAMAccountName={username}))",
            search_scope=SUBTREE,
            attributes=["sAMAccountName", "givenName", "sn", "mail", "memberOf"],
        )

        if not conn.entries:
            # Bind worked but no matching user object — odd, treat as failure
            return None

        entry = conn.entries[0]
        groups = [str(g) for g in entry.memberOf] if entry.memberOf else []

        full_name = " ".join(
            p for p in [
                str(entry.givenName) if entry.givenName else "",
                str(entry.sn)        if entry.sn        else "",
            ] if p
        ).strip()

        return {
            "username":     str(entry.sAMAccountName),
            "display_name": full_name or username,
            "email":        str(entry.mail) if entry.mail else None,
            "groups":       groups,     # list of DN strings like "CN=IT-Admins,OU=...,DC=hnl,DC=tv"
        }
    finally:
        try:
            conn.unbind()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 2. User sync (insert on first login, update on subsequent logins)
# ---------------------------------------------------------------------------
def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    with get_db_cursor() as cur:
        cur.execute(
            "SELECT UserID, Username, DisplayName, Email, ADGroups, AppRole, IsActive, LastLogin "
            "FROM Users WHERE Username = ?",
            username,
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "UserID":      row[0],
            "Username":    row[1],
            "DisplayName": row[2],
            "Email":       row[3],
            "ADGroups":    row[4],
            "AppRole":     row[5],
            "IsActive":    bool(row[6]),
            "LastLogin":   row[7],
        }


def sync_user(ad_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert the user if new (AppRole defaults to 'Viewer'), or update
    DisplayName / Email / ADGroups / LastLogin if they already exist.
    Returns the up-to-date user row as a dict.
    """
    username      = ad_info["username"]
    display_name  = ad_info["display_name"]
    email         = ad_info["email"]
    groups_csv    = ";".join(ad_info["groups"]) if ad_info["groups"] else None

    existing = get_user_by_username(username)

    with get_db_cursor(commit=True) as cur:
        if existing is None:
            cur.execute(
                "INSERT INTO Users (Username, DisplayName, Email, ADGroups, AppRole, LastLogin) "
                "VALUES (?, ?, ?, ?, 'Viewer', GETDATE())",
                username, display_name, email, groups_csv,
            )
        else:
            cur.execute(
                "UPDATE Users "
                "SET DisplayName = ?, Email = ?, ADGroups = ?, LastLogin = GETDATE() "
                "WHERE Username = ?",
                display_name, email, groups_csv, username,
            )

    return get_user_by_username(username)


# ---------------------------------------------------------------------------
# 3. Convenience wrapper
# ---------------------------------------------------------------------------
def authenticate_and_sync(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Full login flow:
      - Bind to AD
      - If bind fails, return None
      - If bind succeeds, upsert Users row
      - If the user's IsActive is 0, refuse login
    """
    ad_info = authenticate_ad(username, password)
    if ad_info is None:
        return None

    user_row = sync_user(ad_info)

    if not user_row["IsActive"]:
        return None

    return user_row


# ---------------------------------------------------------------------------
# Manual test — run with:  python auth.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import getpass
    u = input("AD username: ").strip()
    p = getpass.getpass("AD password: ")
    result = authenticate_and_sync(u, p)
    if result is None:
        print("[-] Login failed.")
    else:
        print("[+] Login OK:")
        for k, v in result.items():
            print(f"    {k}: {v}")