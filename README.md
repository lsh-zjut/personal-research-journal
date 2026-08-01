# 研迹 · 个人科研日志

一个轻量的本地科研日志网页。可以按日期记录每日科研进展、上传多张实验图片，并通过月历或历史搜索回顾以前的工作。

## 功能

- 每个日期保存一篇日志，可随时继续修改
- 记录标题、正文、研究状态和标签
- 上传 PNG、JPG、GIF、WebP 图片，支持多图和拖放
- 月历标记已有日志的日期
- 按标题、正文或标签搜索历史记录
- SQLite 本地存储，无需安装数据库服务
- 桌面端和手机端自适应

## 启动

项目已经使用 Conda 环境名 `research-journal`。在 Anaconda Prompt 或 PowerShell 中执行：

```bash
cd D:\ZJUT\personal_journal
conda activate research-journal
python app.py
```

浏览器打开 <http://127.0.0.1:5000>。按 `Ctrl+C` 停止服务。

也可以直接双击项目中的 `start_journal.bat` 启动。

如果换了一台电脑，可在项目目录重新创建环境：

```bash
conda env create -f environment.yml
conda activate research-journal
python app.py
```

## 数据与备份

日志数据位于 `instance/journal.db`，图片位于 `uploads/`。这两个位置已在 `.gitignore` 中排除，不会被提交到公开 GitHub 仓库。

备份时请同时复制：

```text
instance/journal.db
uploads/
```

## 测试

```bash
python -m unittest discover -s tests -v
```

## 上传 GitHub

首次上传前，在项目目录运行：

```bash
git init
git add .
git commit -m "Initial research journal website"
git branch -M main
git remote add origin https://github.com/你的用户名/你的仓库名.git
git push -u origin main
```

建议将 GitHub 仓库设为私有。源码中不包含日志数据库和上传的科研图片。
