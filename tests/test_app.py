import io
import tempfile
import unittest
from pathlib import Path

from app import create_app, hash_password


class JournalAppTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "VISITOR_PASSWORD_HASH": hash_password("visitor-password", iterations=1_000),
                "ADMIN_PASSWORD_HASH": hash_password("admin-password", iterations=1_000),
                "DATABASE": root / "test.db",
                "UPLOAD_FOLDER": root / "uploads",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def csrf_token(self):
        self.client.get("/login")
        with self.client.session_transaction() as session:
            return session["csrf_token"]

    def login(self, password="visitor-password"):
        return self.client.post(
            "/login",
            data={"csrf_token": self.csrf_token(), "password": password},
            follow_redirects=True,
        )

    def test_private_pages_require_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/login")

    def test_login_home_and_history_render(self):
        self.assertIn("密码不正确".encode(), self.login("wrong").data)
        self.assertIn("访客验证成功".encode(), self.login().data)
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/history").status_code, 200)

    def test_login_rate_limit(self):
        for _attempt in range(8):
            self.assertEqual(self.login("wrong").status_code, 200)
        self.assertEqual(self.login("wrong").status_code, 429)

    def test_visitor_is_read_only_even_with_direct_requests(self):
        self.login()
        token = self.csrf_token()
        response = self.client.post(
            "/save",
            data={
                "csrf_token": token,
                "entry_date": "2026-08-02",
                "title": "不应保存",
                "content": "访客不能写入。",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("仅管理员".encode(), response.data)

        with self.app.app_context():
            from app import query_one

            entry = query_one(
                self.app, "SELECT * FROM entries WHERE entry_date = ?", ("2026-08-02",)
            )
        self.assertIsNone(entry)
        self.assertNotIn("保存科研日志".encode(), self.client.get("/").data)

    def test_create_update_search_and_delete_entry(self):
        self.login("admin-password")
        token = self.csrf_token()
        response = self.client.post(
            "/save",
            data={
                "csrf_token": token,
                "entry_date": "2026-08-01",
                "title": "模型消融实验",
                "content": "完成基线实验并记录结果。",
                "progress": "取得进展",
                "tags": "消融实验, 模型",
                "images": (io.BytesIO(b"fake image content"), "result.png"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("模型消融实验".encode(), response.data)

        search = self.client.get("/history?q=%E6%B6%88%E8%9E%8D")
        self.assertIn("模型消融实验".encode(), search.data)

        with self.app.app_context():
            from app import query_one

            entry = query_one(self.app, "SELECT * FROM entries WHERE entry_date = ?", ("2026-08-01",))
            image = query_one(self.app, "SELECT * FROM images WHERE entry_id = ?", (entry["id"],))

        response = self.client.post(
            f"/image/{image['id']}/delete",
            data={"csrf_token": token},
            follow_redirects=True,
        )
        self.assertIn("图片已删除".encode(), response.data)

        response = self.client.post(
            f"/entry/{entry['id']}/delete",
            data={"csrf_token": token},
            follow_redirects=True,
        )
        self.assertIn("该日科研日志已删除".encode(), response.data)

    def test_rejects_post_without_csrf(self):
        self.login("admin-password")
        response = self.client.post("/save", data={})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
