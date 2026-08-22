# GitHub + VPS 部署

## 重要提醒

研申当前没有多用户登录系统。**不要把 8000 端口直接开放到公网**，否则任何访问者都可能查看题库、修改设置或读取已保存的 API Key。默认部署只监听 VPS 的 `127.0.0.1`，推荐用 SSH 隧道、Tailscale/WireGuard 或带鉴权的反向代理访问。

题目、材料和参考答案仅供个人学习使用，GitHub 仓库建议保持 **Private**。

## 1. 上传到 GitHub

在本机执行：

```powershell
cd D:\program\YanShen
git status
git add .
git commit -m "feat: add VPS Docker deployment"
git branch -M main
git remote add origin git@github.com:<你的用户名>/<你的仓库名>.git
git push -u origin main
```

如果已有远程仓库，把第 5 步改为：

```powershell
git remote set-url origin git@github.com:<你的用户名>/<你的仓库名>.git
git push -u origin main
```

## 2. 准备 VPS

在 Ubuntu/Debian VPS 上安装 Docker：

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

退出后重新登录，让 Docker 用户组生效。

## 3. 拉取并启动

```bash
git clone git@github.com:<你的用户名>/<你的仓库名>.git yanshen
cd yanshen
docker compose up -d --build
docker compose logs -f
```

首次构建需要下载模型运行依赖，可能耗时几分钟。启动后可按 `Ctrl+C` 退出日志；容器会继续后台运行。

检查服务：

```bash
curl -fsS http://127.0.0.1:8000/health
```

应返回：

```text
ok
```

## 4. 从自己的电脑访问

默认端口只绑定在 VPS 的 `127.0.0.1`。在你本机打开 PowerShell：

```powershell
ssh -N -L 8000:127.0.0.1:8000 <vps用户>@<VPS公网IP>
```

保持这个窗口不关闭，然后浏览器访问：

```text
http://127.0.0.1:8000
```

如果使用 Tailscale/WireGuard，可以把 `docker-compose.yml` 里的 `127.0.0.1:8000:8000` 改成 VPN 内网 IP 对应的绑定地址，但仍然不要直接暴露到公网。

## 5. 数据与备份

个人数据保存在 Docker named volume 中，不是仓库里的 `data/` 目录。查看数据卷：

```bash
docker volume ls
docker compose exec yanshen ls -la /data
```

备份数据库：

```bash
mkdir -p backup
docker compose cp yanshen:/data/gongkao.sqlite3 backup/gongkao.sqlite3
```

恢复时先停止服务，再把备份复制回去：

```bash
docker compose down
docker compose up -d
docker compose cp backup/gongkao.sqlite3 yanshen:/data/gongkao.sqlite3
docker compose restart
```

## 6. 更新版本

```bash
cd yanshen
git pull
docker compose up -d --build
docker image prune -f
```

应用启动时会自动升级本地数据库，并把镜像内置的题目/答案种子同步到你的用户数据库；私人作答和批改记录不会被种子覆盖。
