# 本机电脑通过阿里云 ECS mihomo 代理运行 Codex CLI 教程

## 0. 目标

把阿里云 ECS 配成代理跳板机：

```text
本机电脑 -> ECS 上的 mihomo/Clash-Meta -> OpenAI / GitHub / npm
```

本文里的“本机电脑”指你手上要运行 `codex` 命令的电脑；“ECS”指运行 mihomo 的阿里云服务器。

适用场景：

```text
1. ECS 可以运行 mihomo。
2. 本机电脑不能安装 mihomo，或不方便配置 Clash 客户端。
3. 本机电脑可以访问 ECS 公网 IP。
4. 你希望本机电脑运行 Codex CLI 时走 ECS 的代理出口。
5. 你需要浏览器远程打开 mihomo 控制面板切换节点。
```

## 1. 安装 mihomo

官方发布页：

```text
https://github.com/MetaCubeX/mihomo/releases
```

先确认 ECS 架构：

```bash
uname -m
```

### x86_64 推荐版

如果输出是 `x86_64`，优先用 amd64 v3：

```bash
cd /tmp
wget https://github.com/MetaCubeX/mihomo/releases/download/v1.19.24/mihomo-linux-amd64-v3-v1.19.24.gz
gunzip mihomo-linux-amd64-v3-v1.19.24.gz
chmod +x mihomo-linux-amd64-v3-v1.19.24
file mihomo-linux-amd64-v3-v1.19.24
sudo mv mihomo-linux-amd64-v3-v1.19.24 /usr/local/bin/mihomo
mihomo -v
```

如果运行时报 CPU 指令集不支持，换 amd64 v1：

```bash
cd /tmp
wget https://github.com/MetaCubeX/mihomo/releases/download/v1.19.24/mihomo-linux-amd64-v1-v1.19.24.gz
gunzip mihomo-linux-amd64-v1-v1.19.24.gz
chmod +x mihomo-linux-amd64-v1-v1.19.24
file mihomo-linux-amd64-v1-v1.19.24
sudo mv mihomo-linux-amd64-v1-v1.19.24 /usr/local/bin/mihomo
mihomo -v
```

### ARM64 版本

如果输出是 `aarch64`：

```bash
cd /tmp
wget https://github.com/MetaCubeX/mihomo/releases/download/v1.19.24/mihomo-linux-arm64-v1.19.24.gz
gunzip mihomo-linux-arm64-v1.19.24.gz
chmod +x mihomo-linux-arm64-v1.19.24
file mihomo-linux-arm64-v1.19.24
sudo mv mihomo-linux-arm64-v1.19.24 /usr/local/bin/mihomo
mihomo -v
```

`file` 用来确认下载的是 Linux 可执行文件，正常会看到 `ELF 64-bit`。

## 2. 准备配置文件

配置目录：

```bash
sudo mkdir -p /usr/local/etc/clash
```

配置文件路径：

```text
/usr/local/etc/clash/config.yaml
```

如果服务商提供 Clash/Mihomo 订阅链接：

```bash
cd /usr/local/etc/clash
sudo curl -L -o config.yaml "把你的订阅链接粘贴到这里"
```

检查文件前 40 行，确认不是错误页面。这条命令只读取文件，不会修改配置：

```bash
sed -n '1,40p' /usr/local/etc/clash/config.yaml
```

已有配置先备份：

```bash
sudo cp /usr/local/etc/clash/config.yaml /usr/local/etc/clash/config.yaml.bak.$(date +%Y%m%d%H%M%S)
```

## 3. mihomo 关键配置

编辑配置：

```bash
sudo nano /usr/local/etc/clash/config.yaml
```

顶部建议保留这些配置：

```yaml
port: 7890
socks-port: 7891
allow-lan: true
mode: Rule
log-level: info

external-controller: 0.0.0.0:9090
external-ui: dashboard
secret: <DASHBOARD_SECRET>

authentication:
  - "<PROXY_USER>:<PROXY_PASSWORD>"

dns:
  enable: false
```

含义：

```text
7890: HTTP/HTTPS 代理端口
7891: SOCKS5 代理端口
allow-lan: true: 允许本机电脑访问 ECS 代理
authentication: 本机电脑连接代理时用的用户名和密码
external-controller: 9090 控制 API
secret: 控制 API / 控制面板密码，不是代理密码
external-ui: dashboard: Web 面板目录，对应 /usr/local/etc/clash/dashboard
```

可以先写 `external-ui: dashboard` 再安装面板。没安装面板时，mihomo 通常仍能启动，`9090` API 可用，只是网页面板打不开。

## 4. 安装控制面板 MetaCubeXD

项目地址：

```text
https://github.com/MetaCubeX/metacubexd
```

方式 A：用 Git 克隆：

```bash
sudo apt update
sudo apt install -y git
sudo git clone https://github.com/MetaCubeX/metacubexd.git -b gh-pages /usr/local/etc/clash/dashboard
```

方式 B：下载 release 压缩包：

```bash
cd /tmp
wget https://github.com/MetaCubeX/metacubexd/releases/download/v1.187.1/compressed-dist.tgz
sudo mkdir -p /usr/local/etc/clash/dashboard
sudo tar -zxvf compressed-dist.tgz -C /usr/local/etc/clash/dashboard
```

如果版本变了，到这里复制最新 `compressed-dist.tgz` 链接：

```text
https://github.com/MetaCubeX/metacubexd/releases
```

浏览器访问：

```text
http://<ECS_PUBLIC_IP>:9090/ui
```

控制器信息：

```text
Host: http://<ECS_PUBLIC_IP>:9090
Secret: <DASHBOARD_SECRET>
```

不要在本机浏览器里填 `0.0.0.0:9090`。远程访问要填 ECS 公网 IP。

## 5. 创建 systemd 服务

创建服务文件：

```bash
sudo nano /etc/systemd/system/mihomo.service
```

写入：

```ini
[Unit]
Description=mihomo Proxy Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/mihomo -d /usr/local/etc/clash
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启动并设置开机自启：

```bash
sudo systemctl daemon-reload
sudo systemctl enable mihomo
sudo systemctl start mihomo
sudo systemctl status mihomo --no-pager
```

常用命令：

```bash
mihomo -t -d /usr/local/etc/clash
sudo systemctl restart mihomo
journalctl -u mihomo -n 80 --no-pager
journalctl -u mihomo -o cat -f
```

正常日志会看到：

```text
RESTful API listening at: [::]:9090
HTTP proxy listening at: [::]:7890
SOCKS proxy listening at: [::]:7891
```

首次启动如果卡在 `geoip.metadb` 下载，可以在另一台能访问 GitHub 的机器下载：

```bash
wget https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip.metadb
```

然后上传到：

```text
/usr/local/etc/clash/geoip.metadb
```

再重启：

```bash
sudo systemctl restart mihomo
```

## 6. 阿里云安全组

只允许你的本机电脑公网 IP 访问这些端口：

```text
TCP 7890  # HTTP/HTTPS 代理
TCP 7891  # SOCKS5 代理
TCP 9090  # mihomo 控制面板
```

不要对 `0.0.0.0/0` 开放，否则 ECS 会变成公开代理。

## 7. 本机电脑通过 ECS 代理运行 Codex

临时设置代理：

```bash
export http_proxy=http://<PROXY_USER>:<PROXY_PASSWORD>@<ECS_PUBLIC_IP>:7890
export https_proxy=http://<PROXY_USER>:<PROXY_PASSWORD>@<ECS_PUBLIC_IP>:7890
export all_proxy=socks5://<PROXY_USER>:<PROXY_PASSWORD>@<ECS_PUBLIC_IP>:7891
codex
```

占位符含义：

```text
<PROXY_USER>: 代理用户名
<PROXY_PASSWORD>: 代理密码
<ECS_PUBLIC_IP>: ECS 公网 IP
```

也可以保存成 alias：

```bash
echo "alias codex_proxy='export http_proxy=http://<PROXY_USER>:<PROXY_PASSWORD>@<ECS_PUBLIC_IP>:7890 https_proxy=http://<PROXY_USER>:<PROXY_PASSWORD>@<ECS_PUBLIC_IP>:7890 all_proxy=socks5://<PROXY_USER>:<PROXY_PASSWORD>@<ECS_PUBLIC_IP>:7891 && codex'" >> ~/.bashrc
source ~/.bashrc
```

如果用 zsh，把 `~/.bashrc` 换成 `~/.zshrc`。

以后运行：

```bash
codex_proxy
```

## 8. 测试代理

```bash
curl -i -x http://<PROXY_USER>:<PROXY_PASSWORD>@<ECS_PUBLIC_IP>:7890 https://api.openai.com
curl -i -x http://<PROXY_USER>:<PROXY_PASSWORD>@<ECS_PUBLIC_IP>:7890 https://www.google.com
curl -i -x http://<PROXY_USER>:<PROXY_PASSWORD>@<ECS_PUBLIC_IP>:7890 https://registry.npmjs.org/@openai%2fcodex
```

安装 Codex CLI 时访问的是具体包地址：

```text
https://registry.npmjs.org/@openai%2fcodex
```

不要只测 npm 根路径 `https://registry.npmjs.org/`。

## 9. Codex CLI 安装和更新

Codex CLI npm 包：

```text
https://www.npmjs.com/package/@openai/codex
```

正常安装或更新：

```bash
npm install -g @openai/codex@latest
codex --version
```

走 ECS 代理安装或更新：

```bash
http_proxy=http://<PROXY_USER>:<PROXY_PASSWORD>@<ECS_PUBLIC_IP>:7890 \
https_proxy=http://<PROXY_USER>:<PROXY_PASSWORD>@<ECS_PUBLIC_IP>:7890 \
npm install -g @openai/codex@latest --registry=https://registry.npmjs.org/
```

## 10. npm registry 不通时

如果 OpenAI 和 Google 都通，但 npm 包地址失败：

```text
HTTP/1.1 200 Connection established
curl: (35) Recv failure: Connection reset by peer
```

说明本机电脑已连上 ECS 代理，但当前节点访问 npm registry 被重置。

先在控制面板切换 `⚡️ 代理` 节点，每切一次测试：

```bash
curl -i -x http://<PROXY_USER>:<PROXY_PASSWORD>@<ECS_PUBLIC_IP>:7890 https://registry.npmjs.org/@openai%2fcodex
```

如果经常不稳定，可以在 `rules:` 最前面加：

```yaml
rules:
- DOMAIN,registry.npmjs.org,⚡️ 代理
- DOMAIN-SUFFIX,npmjs.org,⚡️ 代理
- DOMAIN-SUFFIX,npmjs.com,⚡️ 代理

# 后面继续你的原规则
```

`⚡️ 代理` 必须是 `config.yaml` 里真实存在的策略组名。改完检查并重启：

```bash
mihomo -t -d /usr/local/etc/clash
sudo systemctl restart mihomo
```

还不行就用离线包。在另一台能访问 npm 的电脑上：

```bash
npm pack @openai/codex@latest
```

把生成的 `openai-codex-*.tgz` 拷到本机电脑：

```bash
npm install -g ./openai-codex-*.tgz
codex --version
```

## 11. Codex 无法登录时迁移 auth.json

优先正常登录：

```bash
codex
```

如果本机电脑一直无法完成登录，但另一台你自己的电脑已经登录过 Codex，可以迁移登录文件。

已登录电脑上确认：

```bash
ls -l ~/.codex/auth.json
```

本机电脑准备目录：

```bash
mkdir -p ~/.codex
```

复制已登录电脑的：

```text
~/.codex/auth.json
```

到本机电脑同一路径：

```text
~/.codex/auth.json
```

如果可以用 `scp`：

```bash
scp <USER>@<LOGGED_IN_MACHINE_IP>:~/.codex/auth.json ~/.codex/auth.json
chmod 600 ~/.codex/auth.json
codex
```

不能用 `scp` 时，用 U 盘、文件传输工具或远程桌面复制文件也可以。

注意：`auth.json` 是敏感登录凭据，只在自己的电脑之间迁移，不要发给别人，不要上传到 Git 仓库、公开网盘或聊天群。

## 12. 常见问题

### 代理认证失败

确认本机电脑代理 URL 和配置一致：

```yaml
authentication:
  - "<PROXY_USER>:<PROXY_PASSWORD>"
```

```text
http://<PROXY_USER>:<PROXY_PASSWORD>@<ECS_PUBLIC_IP>:7890
```

### 控制面板打不开

检查配置、安全组和服务：

```yaml
external-controller: 0.0.0.0:9090
external-ui: dashboard
secret: <DASHBOARD_SECRET>
```

```text
TCP 9090
```

```bash
systemctl status mihomo --no-pager
journalctl -u mihomo -n 80 --no-pager
```

远程浏览器里的 Endpoint URL 填：

```text
http://<ECS_PUBLIC_IP>:9090
```

Secret 填：

```text
<DASHBOARD_SECRET>
```

### 本机电脑代理不通

检查：

```yaml
allow-lan: true
port: 7890
socks-port: 7891
authentication:
  - "<PROXY_USER>:<PROXY_PASSWORD>"
```

安全组至少放行：

```text
TCP 7890
TCP 7891
```

### npm 安装 Codex 失败

先测具体包地址：

```bash
curl -i -x http://<PROXY_USER>:<PROXY_PASSWORD>@<ECS_PUBLIC_IP>:7890 https://registry.npmjs.org/@openai%2fcodex
```

失败就切换 mihomo 节点；一直失败就用 `npm pack` 离线包。

## 13. 踩坑总结

1. `secret` 是控制台密码，不是代理密码。
2. 代理认证用 `authentication`。
3. `allow-lan: true` 必须开启。
4. 安全组只放行自己的本机电脑公网 IP。
5. npm 根路径通，不代表 `@openai/codex` 包地址通。
6. `HTTP/1.1 200 Connection established` 后 reset，说明本机电脑连上代理了，但当前节点访问目标失败。
7. npm 安装不稳定时，用 `npm pack` 离线安装。
8. 首次启动失败时看 `journalctl -u mihomo -n 120 --no-pager`，常见原因是 `geoip.metadb` 下载超时。
9. `~/.codex/auth.json` 是敏感凭据，只能在自己的电脑之间迁移。

## 14. 参考链接

```text
mihomo releases:
https://github.com/MetaCubeX/mihomo/releases

MetaCubeXD:
https://github.com/MetaCubeX/metacubexd

MetaCubeX 官方文档:
https://wiki.metacubex.one/

Linux.do 参考文章:
https://linux.do/t/topic/885119

Codex CLI npm 包:
https://www.npmjs.com/package/@openai/codex
```
