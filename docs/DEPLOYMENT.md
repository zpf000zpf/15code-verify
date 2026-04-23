# 部署指南

## 1. 开发模式（本地跑起来看效果）

```bash
# 核心包
cd packages/core && pip install -e ".[dev]"

# API 后端
cd ../../apps/api
pip install -r requirements.txt
uvicorn verify_api.main:app --reload --port 8000

# Web 前端
cd ../web
npm install
npm run dev
# 访问 http://localhost:3000
```

## 2. CLI 安装

```bash
cd packages/core && pip install -e .
cd ../../apps/cli && pip install -e .

verify --help
```

## 3. Docker 一键部署

```bash
cd deploy/docker
cp .env.example .env
docker compose up -d --build
```

## 4. 生产部署（K8s 示意）

- Web：Next.js → Vercel / Cloudflare Pages / 自建
- API：FastAPI → K8s Deployment + HPA
- 队列：Redis（BullMQ 或 arq）
- 持久化：PostgreSQL 存 scan 元数据，ClickHouse 存时序监控
- 对象存储：报告 JSON 归档

## 5. Ground Truth 基线刷新（可选）

为了提高识别准确度，15code 团队自己维护一个每周运行的 cron job，
用官方 Anthropic / OpenAI / Gemini key 对每个主力模型跑一遍基线探针，
把结果存入 `data/baselines/{date}.json`。

**重要**：基线刷新**只用 15code 自己的 key**，永远不会使用用户提供的 key。
