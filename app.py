import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import date, datetime
from functools import wraps
from pathlib import Path
from threading import Lock

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix


BASE_DIR = Path(__file__).resolve().parent
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
PASSWORD_HASH_ITERATIONS = 600_000
VALID_ROLES = {"visitor", "admin"}
LOGIN_ATTEMPT_LIMIT = 8
LOGIN_ATTEMPT_WINDOW = 15 * 60


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=load_or_create_secret_key(),
        VISITOR_PASSWORD_HASH=load_password_hash("visitor"),
        ADMIN_PASSWORD_HASH=load_password_hash("admin"),
        DATABASE=BASE_DIR / "instance" / "journal.db",
        UPLOAD_FOLDER=BASE_DIR / "uploads",
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=environment_flag("JOURNAL_COOKIE_SECURE", False),
        SESSION_COOKIE_NAME="research_journal_session",
        TRUSTED_HOSTS=load_trusted_hosts(),
    )
    if test_config:
        app.config.update(test_config)

    if environment_flag("JOURNAL_BEHIND_PROXY", False):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    init_db(app)
    login_failures = {}
    login_failures_lock = Lock()

    @app.context_processor
    def inject_globals():
        return {
            "csrf_token": get_csrf_token(),
            "today": date.today().isoformat(),
            "is_admin": session.get("role") == "admin",
        }

    @app.before_request
    def require_login():
        if request.endpoint in {"login", "static"}:
            return None
        if session.get("role") not in VALID_ROLES:
            return redirect(url_for("login"))
        return None

    @app.before_request
    def check_csrf():
        if request.method == "POST":
            submitted = request.form.get("csrf_token", "")
            expected = session.get("csrf_token", "")
            if not expected or not hmac.compare_digest(submitted, expected):
                abort(400, "表单已过期，请刷新页面后重试。")

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "private, no-store"
        return response

    @app.route("/login", methods=("GET", "POST"))
    def login():
        if session.get("role") in VALID_ROLES:
            return redirect(url_for("index"))
        if request.method == "POST":
            client_address = request.remote_addr or "unknown"
            if login_is_limited(login_failures, login_failures_lock, client_address):
                flash("尝试次数过多，请 15 分钟后再试。", "error")
                return render_template("login.html"), 429
            password = request.form.get("password", "")
            visitor_match = verify_password(password, app.config["VISITOR_PASSWORD_HASH"])
            admin_match = verify_password(password, app.config["ADMIN_PASSWORD_HASH"])
            role = "admin" if admin_match else "visitor" if visitor_match else None
            if role:
                clear_login_failures(login_failures, login_failures_lock, client_address)
                session.clear()
                session["role"] = role
                flash(
                    "管理员验证成功，可以编辑日志。"
                    if role == "admin"
                    else "访客验证成功，当前为只读模式。",
                    "success",
                )
                return redirect(url_for("index"))
            record_login_failure(login_failures, login_failures_lock, client_address)
            flash("密码不正确，请重新输入。", "error")
        return render_template("login.html")

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/")
    def index():
        selected = parse_date(request.args.get("date")) or date.today()
        entry = query_one(
            app,
            "SELECT * FROM entries WHERE entry_date = ?",
            (selected.isoformat(),),
        )
        images = []
        if entry:
            images = query_all(
                app,
                "SELECT * FROM images WHERE entry_id = ? ORDER BY created_at",
                (entry["id"],),
            )

        entry_dates = [
            row["entry_date"]
            for row in query_all(app, "SELECT entry_date FROM entries ORDER BY entry_date")
        ]
        stats = query_one(
            app,
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN entry_date >= date('now', '-6 days') THEN 1 ELSE 0 END) AS week
            FROM entries
            """,
        )
        return render_template(
            "index.html",
            selected_date=selected.isoformat(),
            selected_label=format_chinese_date(selected),
            entry=entry,
            images=images,
            entry_dates=entry_dates,
            stats=stats,
        )

    @app.post("/save")
    @admin_required
    def save_entry():
        entry_date = parse_date(request.form.get("entry_date"))
        if not entry_date:
            flash("请选择有效日期。", "error")
            return redirect(url_for("index"))

        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        progress = request.form.get("progress", "进行中").strip()
        tags = request.form.get("tags", "").strip()
        if not title or not content:
            flash("标题和日志内容不能为空。", "error")
            return redirect(url_for("index", date=entry_date.isoformat()))

        now = datetime.now().isoformat(timespec="seconds")
        with database(app) as db:
            db.execute(
                """
                INSERT INTO entries (entry_date, title, content, progress, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entry_date) DO UPDATE SET
                    title = excluded.title,
                    content = excluded.content,
                    progress = excluded.progress,
                    tags = excluded.tags,
                    updated_at = excluded.updated_at
                """,
                (entry_date.isoformat(), title, content, progress, tags, now, now),
            )
            entry_id = db.execute(
                "SELECT id FROM entries WHERE entry_date = ?", (entry_date.isoformat(),)
            ).fetchone()["id"]
            for upload in request.files.getlist("images"):
                if not upload or not upload.filename:
                    continue
                if not allowed_file(upload.filename):
                    flash(f"已跳过不支持的图片：{upload.filename}", "error")
                    continue
                original_name = secure_filename(upload.filename) or "image"
                extension = original_name.rsplit(".", 1)[1].lower()
                stored_name = f"{uuid.uuid4().hex}.{extension}"
                upload.save(Path(app.config["UPLOAD_FOLDER"]) / stored_name)
                db.execute(
                    "INSERT INTO images (entry_id, filename, original_name, created_at) VALUES (?, ?, ?, ?)",
                    (entry_id, stored_name, original_name, now),
                )
            db.commit()

        flash("科研日志已保存。", "success")
        return redirect(url_for("index", date=entry_date.isoformat()))

    @app.post("/entry/<int:entry_id>/delete")
    @admin_required
    def delete_entry(entry_id):
        entry = query_one(app, "SELECT * FROM entries WHERE id = ?", (entry_id,))
        if not entry:
            abort(404)
        images = query_all(app, "SELECT filename FROM images WHERE entry_id = ?", (entry_id,))
        with database(app) as db:
            db.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
            db.commit()
        for image in images:
            delete_file_safely(app, image["filename"])
        flash("该日科研日志已删除。", "success")
        return redirect(url_for("index", date=entry["entry_date"]))

    @app.post("/image/<int:image_id>/delete")
    @admin_required
    def delete_image(image_id):
        image = query_one(
            app,
            """
            SELECT images.*, entries.entry_date
            FROM images JOIN entries ON images.entry_id = entries.id
            WHERE images.id = ?
            """,
            (image_id,),
        )
        if not image:
            abort(404)
        with database(app) as db:
            db.execute("DELETE FROM images WHERE id = ?", (image_id,))
            db.commit()
        delete_file_safely(app, image["filename"])
        flash("图片已删除。", "success")
        return redirect(url_for("index", date=image["entry_date"]))

    @app.get("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.get("/history")
    def history():
        keyword = request.args.get("q", "").strip()
        if keyword:
            pattern = f"%{keyword}%"
            entries = query_all(
                app,
                """
                SELECT entries.*, COUNT(images.id) AS image_count
                FROM entries LEFT JOIN images ON entries.id = images.entry_id
                WHERE entries.title LIKE ? OR entries.content LIKE ? OR entries.tags LIKE ?
                GROUP BY entries.id ORDER BY entries.entry_date DESC
                """,
                (pattern, pattern, pattern),
            )
        else:
            entries = query_all(
                app,
                """
                SELECT entries.*, COUNT(images.id) AS image_count
                FROM entries LEFT JOIN images ON entries.id = images.entry_id
                GROUP BY entries.id ORDER BY entries.entry_date DESC
                """,
            )
        return render_template("history.html", entries=entries, keyword=keyword)

    @app.errorhandler(413)
    def file_too_large(_error):
        flash("上传内容超过 20 MB，请压缩图片后重试。", "error")
        return redirect(request.referrer or url_for("index"))

    @app.errorhandler(403)
    def forbidden(_error):
        return "仅管理员可以修改科研日志。", 403

    return app


def connect_db(app):
    connection = sqlite3.connect(app.config["DATABASE"])
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def database(app):
    connection = connect_db(app)
    try:
        yield connection
    finally:
        connection.close()


def init_db(app):
    with database(app) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_date TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                progress TEXT NOT NULL DEFAULT '进行中',
                tags TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER NOT NULL,
                filename TEXT NOT NULL UNIQUE,
                original_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE
            );
            """
        )


def query_one(app, sql, params=()):
    with database(app) as db:
        return db.execute(sql, params).fetchone()


def query_all(app, sql, params=()):
    with database(app) as db:
        return db.execute(sql, params).fetchall()


def parse_date(value):
    try:
        return date.fromisoformat(value or "")
    except ValueError:
        return None


def format_chinese_date(value):
    weekdays = "一二三四五六日"
    return f"{value.year}年{value.month}月{value.day}日 · 星期{weekdays[value.weekday()]}"


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def delete_file_safely(app, filename):
    target = Path(app.config["UPLOAD_FOLDER"]) / Path(filename).name
    if target.exists():
        target.unlink()


def get_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(24)
    return session["csrf_token"]


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def login_is_limited(failures, lock, client_address):
    cutoff = time.monotonic() - LOGIN_ATTEMPT_WINDOW
    with lock:
        recent = [timestamp for timestamp in failures.get(client_address, []) if timestamp > cutoff]
        failures[client_address] = recent
        return len(recent) >= LOGIN_ATTEMPT_LIMIT


def record_login_failure(failures, lock, client_address):
    with lock:
        failures.setdefault(client_address, []).append(time.monotonic())


def clear_login_failures(failures, lock, client_address):
    with lock:
        failures.pop(client_address, None)


def hash_password(password, *, iterations=PASSWORD_HASH_ITERATIONS):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii")
    encoded_digest = base64.urlsafe_b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${iterations}${encoded_salt}${encoded_digest}"


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, encoded_salt, encoded_digest = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected = base64.urlsafe_b64decode(encoded_digest.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations)
        )
        return hmac.compare_digest(actual, expected)
    except (AttributeError, TypeError, ValueError):
        return False


def load_password_hash(role):
    environment_hash = os.environ.get(f"JOURNAL_{role.upper()}_PASSWORD_HASH", "").strip()
    if environment_hash:
        return environment_hash
    password_file = BASE_DIR / "instance" / f"{role}_password_hash.txt"
    if password_file.exists():
        return password_file.read_text(encoding="utf-8").strip()
    raise RuntimeError(
        f"缺少 {password_file.relative_to(BASE_DIR)}，请先运行 python configure_passwords.py。"
    )


def environment_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_trusted_hosts():
    value = os.environ.get("JOURNAL_TRUSTED_HOSTS", "").strip()
    return [host.strip() for host in value.split(",") if host.strip()] or None


def load_or_create_secret_key():
    environment_secret = os.environ.get("JOURNAL_SECRET_KEY", "").strip()
    if environment_secret:
        return environment_secret
    secret_file = BASE_DIR / "instance" / "secret_key"
    secret_file.parent.mkdir(parents=True, exist_ok=True)
    if not secret_file.exists():
        secret_file.write_text(secrets.token_hex(32), encoding="utf-8")
    return secret_file.read_text(encoding="utf-8").strip()


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
