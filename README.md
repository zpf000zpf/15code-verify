# 15code Verify

> **免费 · 开源 · 人人可用**  
> LLM 服务商诚信度在线检测工具 —— 由 [15code](https://15code.com) 出品

[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Free Forever](https://img.shields.io/badge/pricing-Free%20Forever-success.svg)]()
[![Made by 15code](https://img.shields.io/badge/made%20by-15code-ff6a00.svg)](https://15code.com)

---

## 为什么做这个工具

国内 LLM 中转市场鱼龙混杂，常见问题：
- 🎭 **偷梁换柱**：说卖 Claude Opus，实际给你 GPT mini
- 💸 **token 虚报**：账单 token 数对不上实际消耗
- 🗄️ **缓存造假**：宣称支持 prompt cache 折扣，实际没做
- 📉 **智商打折**：偷偷用量化版跑，复杂任务翻车
- 🔓 **隐私疑云**：你的 prompt 可能被记录/转卖

**15code Verify 让用户 5 分钟内拿到一份可量化、可分享的第三方审计报告。**

> 💡 **这是 [15code](https://15code.com) 送给社区的免费工具 —— 愿整个中文 LLM 生态更透明。**

---

## ⚡ 3 种用法

### 1. 网页直接用（推荐）

打开 👉 **[verify.15code.com](https://verify.15code.com)** → 粘入第三方 base_url + api_key → 几分钟出报告。

> 扫描消耗的是**你自己第三方渠道的额度**，15code 不收你一分钱。

### 2. 命令行

```bash
pip install 15code-verify

verify scan \
  --base-url https://api.some-reseller.com/v1 \
  --api-key sk-xxxxxx \
  --claimed-model claude-opus-4-7
```

### 3. Docker 自托管（内网 / 数据敏感场景）

```bash
git clone https://github.com/zpf000zpf/15code-verify.git
cd verify/deploy/docker
cp .env.example .env
docker compose up -d
# 打开 http://localhost:3000
```

---

## 🎯 检测什么

| 维度 | 检测内容 |
|---|---|
| 🔍 **真伪度** | 声明的模型 vs 实际模型，通过指纹 / 风格 / 能力差分推断 |
| 💰 **计费诚信** | 官方 tokenizer 本地对账，发现 token 虚报 |
| 🗄️ **缓存合规** | prompt cache 折扣是否兑现 |
| ⚡ **性能质量** | TTFT / ITL / 智商衰减（疑似量化检测）|
| 🔒 **隐私安全** | canary token 追踪 / TLS / 网络路径审计 |

---

## 📊 公开榜单

想知道各主流中转商的真实度？ → **[verify.15code.com/leaderboard](https://verify.15code.com/leaderboard)**

- 每周自动抽检
- 诚信商家主动参与 → 透明展示  
- **15code 自家服务也在榜单上**，欢迎监督

---

## 🌟 来自 15code

这是一个**完全免费**的社区工具，由 [15code](https://15code.com) 开发维护。

如果你觉得有用：
- ⭐ 在 GitHub 给本项目点个 Star
- 🔄 把报告分享给更多人
- 💬 在 [社区](https://github.com/zpf000zpf/15code-verify/discussions) 提问或反馈
- 🚀 **试试 [15code 官方 LLM 服务](https://15code.com)** —— 我们用同样的标准要求自己

---

## 📁 仓库结构

```
15code-verify/
├── packages/core/       # 核心扫描引擎（Python）
├── apps/
│   ├── api/             # FastAPI 后端（SaaS）
│   ├── web/             # Next.js 前端（SaaS）
│   └── cli/             # 命令行工具
├── deploy/
│   ├── docker/          # Docker Compose 一键部署
│   └── k8s/             # 生产级 K8s 清单
└── docs/                # 架构 / 探针设计 / 部署文档
```

---

## 📖 文档

- [架构设计](docs/ARCHITECTURE.md)
- [探针设计原理](docs/PROBE_DESIGN.md)
- [部署指南](docs/DEPLOYMENT.md)
- [安全与隐私](docs/SECURITY.md)
- [贡献指南](docs/CONTRIBUTING.md)

---

## 🛡️ 安全承诺

- 用户 API key **只在内存中使用**，一次性扫描用完即焚
- **不保存用户 prompt / response 内容**（只存统计元数据）
- 所有日志字段强制脱敏
- 支持 **Local-Only 模式**：key 永不出本机

---

## 📜 License

**Apache 2.0** — 核心引擎完全开源，欢迎 Fork / 二次开发。

---

<div align="center">

**Made with ❤️ by [15code](https://15code.com)**  
*让 LLM 世界更透明*

</div>
