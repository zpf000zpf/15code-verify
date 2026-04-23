# Docker Compose — 一键部署

```bash
cp .env.example .env
# 编辑 .env 按需填写
docker compose up -d
# Web  → http://localhost:3000
# API  → http://localhost:8000
```

## 停止 / 更新

```bash
docker compose down
docker compose pull && docker compose up -d
```

## 私有部署 / 内网使用

设置：
- `CORS_ORIGINS=https://internal.example.com`
- 不设 `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` → 跳过 Ground Truth 基线（依然可用，仅模型识别准确度略降）
