"""One-time local bootstrap, using getpass or an owner-only private secret file."""

import argparse
import getpass
import json
import os
import stat
from pathlib import Path

from flowlens.auth.accounts import Accounts
from flowlens.storage.sqlite.database import Database
from pydantic import SecretStr


def read_password(path: Path) -> SecretStr:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.geteuid():
            raise ValueError("A private owner-only password file is required.")
        value = stream.read(4098)
        if len(value) > 4097:
            raise ValueError("Password file exceeds limit.")
    decoded = value.decode("utf-8")
    if decoded.endswith("\n"):
        decoded = decoded[:-1]
        if decoded.endswith("\r"):
            decoded = decoded[:-1]
    return SecretStr(decoded)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap one individual administrator")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--login", required=True)
    parser.add_argument("--password-file", type=Path)
    args = parser.parse_args()
    try:
        if args.password_file:
            secret = read_password(args.password_file)
        else:
            if not os.isatty(0):
                raise ValueError("Interactive terminal or private password file required.")
            secret = SecretStr(getpass.getpass("Admin password: "))
            if secret.get_secret_value() != getpass.getpass("Repeat password: "):
                raise ValueError("Passwords differ.")
        with Database(args.database) as database:
            admin = Accounts(database).bootstrap(args.login, secret)
    except Exception:
        raise SystemExit(
            "Admin bootstrap failed; check input, permissions and existing bootstrap."
        ) from None
    print(json.dumps({"id": str(admin.id), "login": admin.login, "status": "created"}))


if __name__ == "__main__":
    main()
