# 研迹 · 个人科研日志

一个使用 Flask 和 SQLite 的科研日志网页。支持按日期记录、图片上传、日历浏览和历史搜索。

## 访问权限

- 访客密码登录后只能查看日志和图片。
- 管理员密码登录后可以新增、修改、上传图片和删除日志。
- 所有写入接口都会在服务端校验管理员身份，不能通过绕过页面获得编辑权限。
- 密码以 PBKDF2-SHA256 哈希保存在本机 `instance/` 目录，不写入源代码，也不会提交到 Git。
- 连续输错密码 8 次后，同一来源会被限制登录 15 分钟。

修改两种密码：

```powershell
& D:\conda\Miniconda\Scripts\conda.exe run -n research-journal python configure_passwords.py
```

修改后重启服务。已经登录的旧会话可能仍然有效；需要立即使所有会话失效时，同时删除 `instance/secret_key`，再重启服务。

## 首次安装

```powershell
cd D:\共享\personal-journal\personal-research-journal
& D:\conda\Miniconda\Scripts\conda.exe env create -f environment.yml
& D:\conda\Miniconda\Scripts\conda.exe run -n research-journal python configure_passwords.py
```

本机调试可双击 `start_journal.bat`，然后访问 <http://127.0.0.1:5000>。

## 发布到 zjut-lsh.cn（推荐）

推荐使用 Cloudflare Tunnel。它从本机主动建立出站加密连接，网页后端仍只监听 `127.0.0.1`，不需要路由器端口映射，也不要在 Windows 防火墙开放 5000、8000、80 或 443 端口。

### 1. 把域名 DNS 托管到 Cloudflare

1. 注册 Cloudflare 账号，在 Domains 中添加 `zjut-lsh.cn`，免费套餐即可。
2. 仔细核对 Cloudflare 扫描出的原有 DNS 记录；如果域名已用于邮箱，必须保留 MX、TXT 等记录。
3. 若腾讯云已开启 DNSSEC，先关闭 DNSSEC。
4. 记下 Cloudflare 分配的两个 NS 地址。
5. 进入腾讯云“域名注册控制台 → 我的域名 → 更多 → 修改 DNS 服务器”。选择“使用非腾讯云 DNS”，填入上一步的两个 NS 地址并提交。
6. 等待 Cloudflare 中域名状态变为 Active 后再继续。

官方参考：

- <https://developers.cloudflare.com/dns/zone-setups/full-setup/setup/>
- <https://cloud.tencent.com/document/product/302/5518>

### 2. 启动本机生产服务

第一次更新环境：

```powershell
cd D:\共享\personal-journal\personal-research-journal
& D:\conda\Miniconda\Scripts\conda.exe env update -n research-journal -f environment.yml --prune
```

之后双击 `start_public.bat`。看到服务运行在 `http://127.0.0.1:8000` 后保持窗口开启。公网环境使用 Waitress，不使用 Flask 自带开发服务器。

### 3. 创建 Cloudflare Tunnel

1. 在 Cloudflare 控制台进入 `Networking → Tunnels`，创建名为 `research-journal` 的 Tunnel。
2. 选择 Windows，复制页面提供的安装命令。
3. 以管理员身份打开 PowerShell，粘贴并运行该命令。命令中包含 Tunnel token，不要发给别人，也不要写入 Git。
4. 等待 Tunnel 显示 `Healthy`。
5. 打开该 Tunnel 的 `Routes`，选择 `Add route → Published application`。
6. 为根域名添加路由：Hostname 选择 `zjut-lsh.cn`，Service URL 填 `http://localhost:8000`。
7. 如需支持 `www.zjut-lsh.cn`，再添加一条相同服务地址的 `www` 路由。
8. 保存后访问 <https://zjut-lsh.cn>。Cloudflare 会负责公网 HTTPS 证书。

官方参考：

- <https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/>
- <https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/>
- <https://flask.palletsprojects.com/en/stable/deploying/waitress/>

### 4. 设置开机运行

Cloudflare 页面给出的 Windows 安装命令会把 `cloudflared` 注册为开机服务。日志后端可使用项目提供的脚本注册开机任务。以管理员身份打开 PowerShell，执行：

```powershell
cd D:\共享\personal-journal\personal-research-journal
Set-ExecutionPolicy -Scope Process Bypass
.\setup_autostart.ps1
```

脚本会创建名为 `ResearchJournal` 的系统启动任务，服务异常退出时每分钟尝试重启。需要移除时执行：

```powershell
.\setup_autostart.ps1 -Remove
```

电脑关机、休眠、断网或批处理窗口关闭时，网站会暂时无法访问。建议关闭自动睡眠，并为数据库设置定期备份。

## 合规提示

自有域名从中国大陆境内设备对公众提供网站服务可能涉及 ICP 备案、接入商和家用宽带条款。Tunnel 解决的是网络暴露与 HTTPS，不代表免除备案或运营商要求。需要长期、稳定、面向境内访客运行时，更稳妥的做法是购买符合备案条件的腾讯云中国大陆服务器并完成 ICP 备案后部署。

腾讯云备案说明：<https://cloud.tencent.com/document/product/243/39038>

## 数据和备份

重要数据都保存在本机：

```text
instance/journal.db
instance/secret_key
instance/visitor_password_hash.txt
instance/admin_password_hash.txt
uploads/
```

备份时至少同时复制 `instance/journal.db` 和 `uploads/`。不要将整个 `instance/` 或 `uploads/` 提交到公开仓库。建议每天自动备份到另一块磁盘，并定期验证备份能否恢复。

## 测试

```powershell
& D:\conda\Miniconda\Scripts\conda.exe run -n research-journal python -m unittest discover -s tests -v
```
