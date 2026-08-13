# 研迹 · 个人科研日志

一个轻量、自托管的科研日志 Web 应用，使用 Flask 和 SQLite 构建。它适合记录每日研究进展、整理实验图片，并通过日历或搜索回顾历史工作。

本项目只提供应用程序源码，不包含作者的日志、图片、密码或其他私人数据。克隆仓库后，每位用户都会在本机创建自己的独立数据。

## 功能

- 按日期创建和更新科研日志
- 记录标题、正文、研究状态和标签
- 上传 PNG、JPG、JPEG、GIF、WebP 图片，单次请求最大 20 MB
- 使用月历查看已有记录的日期
- 按标题、正文或标签搜索历史日志
- 访客与管理员两级权限
- CSRF 防护、登录失败限流和常用安全响应头
- SQLite 本地存储，无需单独安装数据库服务
- 支持桌面端和移动端页面

## 权限模型

应用使用两种密码：

- 访客密码：只能查看日志和图片。
- 管理员密码：可以创建、编辑和删除日志，也可以上传或删除图片。

密码使用 PBKDF2-SHA256 加盐哈希保存，明文密码不会写入源码。所有修改接口都会在服务端再次校验管理员身份。

## 快速开始

### 1. 获取源码

```bash
git clone https://github.com/lsh-zjut/personal-research-journal.git
cd personal-research-journal
```

需要 Python 3.11 或兼容版本。

### 2. 安装依赖

使用 Python 虚拟环境：

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Linux 或 macOS：

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

也可以使用 Conda：

```bash
conda env create -f environment.yml
conda activate research-journal
```

### 3. 配置密码

```bash
python configure_passwords.py
```

程序会分别要求设置访客密码和管理员密码。生成的密码哈希位于 `instance/`，该目录中的私人配置已被 Git 忽略。

### 4. 启动应用

```bash
python app.py
```

浏览器访问 <http://127.0.0.1:5000>。此方式只适合本机使用和开发调试。

## 生产环境部署

不要将 Flask 自带的开发服务器直接暴露到公网。项目依赖中包含 Waitress，可以在生产环境中启动本地后端：

```bash
python -m waitress --listen=127.0.0.1:8000 --threads=4 app:app
```

建议在 Waitress 前使用提供 HTTPS 的反向代理或安全隧道，例如 Nginx、Caddy 或 Cloudflare Tunnel。后端继续监听 `127.0.0.1`，由代理对外提供 HTTPS。

通过 HTTPS 代理运行时，需要配置以下环境变量。PowerShell 示例：

```powershell
$env:JOURNAL_COOKIE_SECURE = "1"
$env:JOURNAL_BEHIND_PROXY = "1"
$env:JOURNAL_TRUSTED_HOSTS = "example.com,www.example.com,localhost,127.0.0.1"
python -m waitress --listen=127.0.0.1:8000 --threads=4 app:app
```

Linux 或 macOS 示例：

```bash
export JOURNAL_COOKIE_SECURE=1
export JOURNAL_BEHIND_PROXY=1
export JOURNAL_TRUSTED_HOSTS=example.com,www.example.com,localhost,127.0.0.1
python -m waitress --listen=127.0.0.1:8000 --threads=4 app:app
```

请将示例域名替换为自己的域名，并确保代理正确设置 `X-Forwarded-For` 和 `X-Forwarded-Proto`。`JOURNAL_COOKIE_SECURE=1` 只应在外部访问已经使用 HTTPS 时启用。

### 环境变量

| 变量 | 用途 |
| --- | --- |
| `JOURNAL_COOKIE_SECURE` | 设为 `1` 后，仅通过 HTTPS 发送会话 Cookie |
| `JOURNAL_BEHIND_PROXY` | 设为 `1` 后，信任一层代理提供的来源地址和协议头 |
| `JOURNAL_TRUSTED_HOSTS` | 允许访问的主机名，多个值使用英文逗号分隔 |
| `JOURNAL_SECRET_KEY` | 可选的 Flask 会话密钥；未设置时会在 `instance/secret_key` 自动生成 |
| `JOURNAL_VISITOR_PASSWORD_HASH` | 可选的访客密码哈希，用于代替本地哈希文件 |
| `JOURNAL_ADMIN_PASSWORD_HASH` | 可选的管理员密码哈希，用于代替本地哈希文件 |

密码哈希环境变量需要使用本项目支持的 PBKDF2-SHA256 格式。一般自托管场景直接运行 `configure_passwords.py` 更方便。

## Windows 辅助脚本

仓库提供以下 Windows 脚本作为部署示例：

- `start_journal.bat`：启动本地开发服务。
- `start_public.bat`：使用 Waitress 启动公网部署后端。
- `setup_autostart.ps1`：注册或移除 Windows 开机启动任务。

这些脚本中的 Python 路径和域名是特定机器的示例配置。使用前请先修改 `PYTHON_EXE` 和 `JOURNAL_TRUSTED_HOSTS`，使其匹配自己的环境。注册开机任务需要以管理员身份运行 PowerShell：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup_autostart.ps1
```

移除任务：

```powershell
.\setup_autostart.ps1 -Remove
```

## 数据与备份

运行时数据默认保存在：

```text
instance/journal.db
instance/secret_key
instance/visitor_password_hash.txt
instance/admin_password_hash.txt
uploads/
```

这些文件不会提交到 Git。备份时至少复制 `instance/journal.db` 和 `uploads/`；如需完整保留登录会话和密码配置，请备份整个 `instance/` 目录。不要把包含真实日志、实验图片或密钥的目录提交到公开仓库。

## 测试

```bash
python -m unittest discover -s tests -v
```

## 适用范围

本项目面向个人或小规模、低并发的自托管使用场景。SQLite、进程内登录限流和本机文件存储不适合作为高并发、多实例的公共服务。公开部署时，请自行配置 HTTPS、系统更新、数据备份和适用地区要求的合规措施。
