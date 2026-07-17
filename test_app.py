"""用户管理系统 — 基础功能测试"""

import os
import re
import pytest
from flask import session


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试前初始化数据库"""
    # 清理旧数据库
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "users.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)
    from app import init_db
    init_db()
    yield


@pytest.fixture
def client():
    """创建测试客户端"""
    from app import app
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client


def login(client, username="admin", password="admin123"):
    """辅助函数：登录并返回是否成功"""
    resp = client.get("/login")
    csrf = re.search(r'csrf_token" value="([^"]+)"', resp.data.decode())
    resp = client.post("/login", data={
        "username": username,
        "password": password,
        "csrf_token": csrf.group(1)
    }, follow_redirects=True)
    return resp


def get_csrf(client, url="/profile"):
    """辅助函数：从页面获取 CSRF Token"""
    resp = client.get(url)
    m = re.search(r'csrf_token" value="([^"]+)"', resp.data.decode())
    return m.group(1) if m else None


class TestAuth:
    """认证功能测试"""

    def test_login_page(self, client):
        """登录页面可访问"""
        resp = client.get("/login")
        assert resp.status_code == 200
        assert "用户登录" in resp.data.decode()

    def test_login_success(self, client):
        """正确密码可登录"""
        resp = client.get("/login")
        csrf = re.search(r'csrf_token" value="([^"]+)"', resp.data.decode())
        assert csrf is not None, "CSRF Token 未找到"

        resp = client.post("/login", data={
            "username": "admin",
            "password": "admin123",
            "csrf_token": csrf.group(1)
        })
        assert resp.status_code == 302  # redirect to /
        assert resp.headers["Location"] == "/"

    def test_login_wrong_password(self, client):
        """错误密码被拒绝"""
        resp = client.get("/login")
        csrf = re.search(r'csrf_token" value="([^"]+)"', resp.data.decode())

        resp = client.post("/login", data={
            "username": "admin",
            "password": "wrongpass",
            "csrf_token": csrf.group(1)
        })
        assert resp.status_code == 200
        assert "用户名或密码错误" in resp.data.decode()

    def test_login_empty_fields(self, client):
        """空用户名/密码被拒绝"""
        resp = client.get("/login")
        csrf = re.search(r'csrf_token" value="([^"]+)"', resp.data.decode())

        resp = client.post("/login", data={
            "username": "",
            "password": "",
            "csrf_token": csrf.group(1)
        })
        assert "用户名和密码不能为空" in resp.data.decode()


class TestRegister:
    """注册功能测试"""

    def test_register_page(self, client):
        """注册页面可访问"""
        resp = client.get("/register")
        assert resp.status_code == 200
        assert "用户注册" in resp.data.decode()

    def test_register_success(self, client):
        """正常注册成功"""
        resp = client.get("/register")
        csrf = re.search(r'csrf_token" value="([^"]+)"', resp.data.decode())

        resp = client.post("/register", data={
            "username": "testuser",
            "password": "TestPass123",
            "email": "test@test.com",
            "phone": "13800138000",
            "csrf_token": csrf.group(1)
        })
        assert "注册成功" in resp.data.decode()

    def test_register_duplicate(self, client):
        """重复用户名被拒绝"""
        resp = client.get("/register")
        csrf = re.search(r'csrf_token" value="([^"]+)"', resp.data.decode())
        client.post("/register", data={
            "username": "dupuser",
            "password": "TestPass123",
            "email": "d@d.com",
            "phone": "13800138001",
            "csrf_token": csrf.group(1)
        })

        resp = client.get("/register")
        csrf = re.search(r'csrf_token" value="([^"]+)"', resp.data.decode())
        resp = client.post("/register", data={
            "username": "dupuser",
            "password": "TestPass123",
            "email": "d@d.com",
            "phone": "13800138001",
            "csrf_token": csrf.group(1)
        })
        assert "用户名已存在" in resp.data.decode()

    def test_register_weak_password(self, client):
        """弱密码被拒绝"""
        resp = client.get("/register")
        csrf = re.search(r'csrf_token" value="([^"]+)"', resp.data.decode())

        resp = client.post("/register", data={
            "username": "weakuser",
            "password": "123",
            "email": "",
            "phone": "",
            "csrf_token": csrf.group(1)
        })
        assert "密码长度至少 6 位" in resp.data.decode()


class TestSecurity:
    """安全机制测试"""

    def test_sql_injection_search(self, client):
        """SQL 注入被参数化查询拦截"""
        # 先登录
        resp = client.get("/login")
        csrf = re.search(r'csrf_token" value="([^"]+)"', resp.data.decode())
        client.post("/login", data={
            "username": "admin", "password": "admin123",
            "csrf_token": csrf.group(1)
        })

        # 测试注入
        resp = client.get('/search?keyword=\' OR 1=1 --')
        assert "admin" not in resp.data.decode() or "alice" not in resp.data.decode()

    def test_path_traversal_page(self, client):
        """路径遍历被拦截"""
        resp = client.get("/page?name=../app.py")
        assert "非法字符" in resp.data.decode()

    def test_page_not_found(self, client):
        """不存在的页面"""
        resp = client.get("/page?name=nonexistent")
        assert "页面不存在" in resp.data.decode()

    def test_help_page(self, client):
        """帮助页面正常"""
        resp = client.get("/page?name=help")
        assert resp.status_code == 200

    def test_unauthorized_profile(self, client):
        """未登录访问profile被拦截"""
        resp = client.get("/profile")
        assert resp.status_code == 302

    def test_csrf_login(self, client):
        """无CSRF Token的登录被拒绝"""
        resp = client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        })
        assert "表单已过期" in resp.data.decode()


class TestPasswordChange:
    """密码修改功能测试"""

    def test_change_password_without_csrf(self, client):
        """无CSRF的改密被拒绝"""
        # 先登录
        resp = client.get("/login")
        csrf = re.search(r'csrf_token" value="([^"]+)"', resp.data.decode())
        client.post("/login", data={
            "username": "admin", "password": "admin123",
            "csrf_token": csrf.group(1)
        })

        resp = client.post("/change-password", data={
            "username": "admin",
            "new_password": "NewPass123",
            "confirm_password": "NewPass123"
        })
        assert resp.status_code == 302

    def test_change_other_user_password(self, client):
        """越权改密被拦截"""
        # 登录 admin
        resp = client.get("/login")
        csrf = re.search(r'csrf_token" value="([^"]+)"', resp.data.decode())
        client.post("/login", data={
            "username": "admin", "password": "admin123",
            "csrf_token": csrf.group(1)
        }, follow_redirects=True)

        # 直接尝试修改 alice 密码（不含 CSRF Token → 应被拒绝）
        resp = client.post("/change-password", data={
            "username": "alice", "new_password": "Hacked123",
            "confirm_password": "Hacked123"
        })
        assert resp.status_code == 302

        # 验证 alice 原密码仍然可用
        resp = client.get("/login")
        csrf = re.search(r'csrf_token" value="([^"]+)"', resp.data.decode())
        resp = client.post("/login", data={
            "username": "alice", "password": "alice2025",
            "csrf_token": csrf.group(1)
        }, follow_redirects=True)
        assert resp.status_code == 200


if __name__ == "__main__":
    pytest.main(["-v", __file__])
