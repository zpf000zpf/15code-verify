# 📘 部署 SOP — 给 15code 运维的 5 分钟部署指南

> 本文档是 **照着贴命令就能部署** 的操作手册。
> 目标环境：Ubuntu 22.04+ / Debian 12 / 带 root / 2vCPU · 4GB RAM 以上

---

## 一、准备工作（你在本地做）

### 1.1 域名 DNS

在 DNS 面板把 `verify.15code.com` 指向你的服务器公网 IP：

```
verify.15code.com   A    <你的服务器 IP>
```

等 2~5 分钟 DNS 生效，确认：
```bash
dig +short verify.15code.com
```

### 1.2 把仓库推到 GitHub（首次）

在你本地 `/home/zpf000zpf/15code-verify` 目录：

```bash
cd /home/zpf000zpf/15code-verify
git init
git add .
git commit -m "initial commit: 15code verify v0.1.0"
git branch -M main
# 建仓库后：
git remote add origin git@github.com:15code/verify.git
git push -u origin main
```

---

## 二、部署（在服务器上做）

### 2.1 SSH 登录

```bash
ssh root@<your-server-ip>
# 或 ssh -i ~/.ssh/your-key.pem ubuntu@<ip>
```

### 2.2 一行命令部署

```bash
curl -fsSL https://raw.githubusercontent.com/15code/verify/main/deploy/install/remote-install.sh | \
  DOMAIN=verify.15code.com EMAIL=ops@15code.com sudo bash
```

**脚本会做**：
- 安装 docker / nginx / certbot
- 克隆仓库到 `/opt/15code-verify`
- 启动 Docker Compose（web + api）
- 配置 nginx 反代
- 申请 Let's Encrypt HTTPS 证书
- 配置 firewall (ufw: 22/80/443)
- 安装 systemd 单元（开机自启）

等 3~5 分钟，屏幕会打印：
```
╭─────────────────────────────────────────────────────────────╮
│  ✅ 15code Verify deployed successfully                      │
│   Web UI     : https://verify.15code.com                     │
│   API        : https://verify.15code.com/api                 │
...
╰─────────────────────────────────────────────────────────────╯
```

### 2.3 验证

```bash
# 浏览器打开
https://verify.15code.com

# 命令行
curl https://verify.15code.com/health
# → {"ok":true,"service":"15code-verify-api","version":"0.1.0"}

curl https://verify.15code.com/v1/leaderboard
```

---

## 三、首次部署后的调优（5 分钟）

### 3.1 填入 Ground Truth 官方 key（可选但推荐）

```bash
vi /opt/15code-verify/deploy/docker/.env
# 填入：
#   ANTHROPIC_API_KEY=sk-ant-...
#   OPENAI_API_KEY=sk-proj-...
systemctl restart 15code-verify
```

### 3.2 生成下载物（pip wheel + tarball）

```bash
cd /opt/15code-verify
./deploy/install/build-artifacts.sh
# 产物放在 /opt/15code-verify/dist/
# nginx 会通过 /download/ 路径对外暴露
```

验证：
```
https://verify.15code.com/download/docker-compose.yml
https://verify.15code.com/download/15code-verify-src.tar.gz
```

### 3.3 配置每周基线刷新（可选）

```bash
crontab -e
# 添加：
0 3 * * 1 /usr/bin/docker exec 15code-verify-api-1 python -m verify_core.ground_truth.refresh
```

---

## 四、日常运维

| 操作 | 命令 |
|---|---|
| 查看日志 | `cd /opt/15code-verify/deploy/docker && docker compose logs -f` |
| 重启服务 | `systemctl restart 15code-verify` |
| 更新到最新版 | `/opt/15code-verify/deploy/install/update.sh` |
| 查看资源 | `docker stats` |
| 备份配置 | `tar -czf /tmp/verify-backup.tar.gz /opt/15code-verify/deploy/docker/.env` |

---

## 五、常见问题

### Q1: certbot 申请失败
- 确认 DNS 已经生效：`dig verify.15code.com` 指向这台机器
- 确认 80 端口没被占用：`ss -tnlp | grep :80`
- 手动重试：`sudo certbot --nginx -d verify.15code.com`

### Q2: docker compose up 报错
```bash
cd /opt/15code-verify/deploy/docker
docker compose logs api
docker compose logs web
```

### Q3: 想把部署换到别的域名
```bash
vi /etc/nginx/sites-available/verify.15code.com
# 改 server_name
nginx -t && systemctl reload nginx
sudo certbot --nginx -d new-domain.com
```

### Q4: 如何下线/卸载
```bash
systemctl disable --now 15code-verify
cd /opt/15code-verify/deploy/docker && docker compose down -v
rm -rf /opt/15code-verify
```

---

## 六、GitHub Actions 自动部署（可选高级）

如果希望每次 push tag 自动部署，在 GitHub 仓库设置：

**Secrets:**
- `DEPLOY_HOST` = 服务器 IP
- `DEPLOY_USER` = `root` 或 `ubuntu`
- `DEPLOY_SSH_KEY` = 用于部署的 SSH 私钥
- `PYPI_API_TOKEN` = PyPI 发布 token（可选）

然后打 tag 即可触发：
```bash
git tag v0.1.0
git push --tags
```

CI 会自动：构建 Docker 镜像 → 推到 ghcr.io → SSH 到服务器执行 update.sh → 发布 PyPI 包 → 创建 GitHub Release。

---

## 七、安全加固（生产必做）

```bash
# 1. 禁用 root SSH 登录
vi /etc/ssh/sshd_config
# PermitRootLogin no
systemctl restart ssh

# 2. 自动安全更新
dpkg-reconfigure -plow unattended-upgrades

# 3. 安装 fail2ban
apt install fail2ban -y
systemctl enable --now fail2ban

# 4. 监控
# 推荐加 Grafana + Loki 或接入你们的日志系统
```

---

**完成后，在浏览器访问 `https://verify.15code.com`，应该看到 15code Verify 首页。**

有问题联系：`ops@15code.com`
