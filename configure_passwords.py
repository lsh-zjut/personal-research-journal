import base64
import hashlib
import hmac
import secrets
from getpass import getpass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
ITERATIONS = 600_000


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii")
    encoded_digest = base64.urlsafe_b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${ITERATIONS}${encoded_salt}${encoded_digest}"


def ask_password(label, minimum_length):
    while True:
        password = getpass(f"请输入新的{label}：")
        if len(password) < minimum_length:
            print(f"{label}至少需要 {minimum_length} 个字符。")
            continue
        confirmation = getpass(f"请再次输入{label}：")
        if not hmac.compare_digest(password, confirmation):
            print("两次输入不一致，请重试。")
            continue
        return password


def main():
    print("密码输入时不会显示在屏幕上。")
    visitor_password = ask_password("访客密码", 4)
    admin_password = ask_password("管理员密码", 10)

    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    (INSTANCE_DIR / "visitor_password_hash.txt").write_text(
        hash_password(visitor_password), encoding="utf-8"
    )
    (INSTANCE_DIR / "admin_password_hash.txt").write_text(
        hash_password(admin_password), encoding="utf-8"
    )
    print("密码已安全更新。请重启日志服务使其生效。")


if __name__ == "__main__":
    main()
