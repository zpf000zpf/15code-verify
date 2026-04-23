# 15code Verify — 架构设计

## 整体架构

```
                      ┌─────────────────────────────┐
                      │   Users (web / cli / sdk)   │
                      └──────────────┬──────────────┘
                                     │ HTTPS
                                     ↓
        ┌──────────────────────────────────────────────────┐
        │  Edge / CDN (Cloudflare)                         │
        └──────────────┬───────────────────────────────────┘
                       ↓
        ┌──────────────────────────────────────────────────┐
        │  apps/web (Next.js 14, Vercel 或 ECS)            │
        │  └─ Server Components + Client Components        │
        └──────────────┬───────────────────────────────────┘
                       ↓ (REST + SSE for progress)
        ┌──────────────────────────────────────────────────┐
        │  apps/api (FastAPI, Python 3.11)                 │
        │  ├─ /v1/scan           创建扫描任务              │
        │  ├─ /v1/scan/{id}      查询进度 / 结果           │
        │  ├─ /v1/report/{id}    报告详情                  │
        │  ├─ /v1/monitor/*      持续监控                  │
        │  └─ /v1/leaderboard    公开榜单                  │
        └──────────────┬───────────────────────────────────┘
                       ↓                   ↓
             ┌─────────────────┐  ┌──────────────────────┐
             │  Redis (BullMQ/  │  │  PostgreSQL          │
             │  RQ 任务队列)    │  │  (用户/任务/报告)    │
             └─────┬───────────┘  └──────────────────────┘
                   ↓
        ┌──────────────────────────────────────────────────┐
        │  Probe Worker Pool (packages/core)               │
        │  ├─ Authenticity Probes                          │
        │  ├─ Tokenizer Oracle (本地 ground truth 对账)    │
        │  ├─ Cache Auditor                                │
        │  ├─ QoS Profiler                                 │
        │  └─ Privacy Canary                               │
        └──────────────┬───────────────────────────────────┘
                       ↓
        ┌──────────────────────────────────────────────────┐
        │  Ground Truth Service                            │
        │  定期直连官方 API，维护各模型指纹基线            │
        │  └─ anthropic / openai / google / deepseek       │
        └──────────────┬───────────────────────────────────┘
                       ↓
        ┌──────────────────────────────────────────────────┐
        │  ClickHouse (时序数据，用于监控 & 榜单)          │
        │  Object Storage (S3/OSS 报告 PDF + 原始 trace)   │
        └──────────────────────────────────────────────────┘
```

## 核心分层

### Layer 1 — Core Engine (`packages/core`)
**与部署方式无关**的纯 Python 包，SaaS / CLI / SDK 共用。

- `verify_core.Scanner` — 扫描编排器，统一入口
- `verify_core.probes` — 探针实现（可插拔）
- `verify_core.tokenizers` — 官方 tokenizer 对账（tiktoken / anthropic count_tokens / sentencepiece）
- `verify_core.cache_audit` — 缓存审计
- `verify_core.scoring` — 置信度融合打分
- `verify_core.ground_truth` — 基线数据访问
- `verify_core.providers` — 各家 API 适配器（OpenAI-compatible / Anthropic / Gemini）

### Layer 2 — Delivery (各 app)
| app | 用途 | 技术栈 |
|---|---|---|
| `apps/api` | SaaS 后端 REST API | FastAPI + SQLAlchemy + RQ |
| `apps/web` | SaaS 前端 | Next.js 14 + Tailwind + shadcn/ui |
| `apps/cli` | 命令行工具 | Typer + Rich |

### Layer 3 — Deployment
| 场景 | 方案 |
|---|---|
| **SaaS 生产** | K8s（ACK/EKS）+ RDS + Redis Cluster + CDN |
| **小规模生产** | Docker Compose（单机 4c8g 可扛 1000 DAU）|
| **私有部署** | Docker Compose 精简版（无监控/无榜单）|
| **零安装** | CLI `pip install` |

## 数据流：一次扫描的完整生命周期

```
[用户] 提交 scan 请求 (base_url + api_key + claimed_model)
  │
  ↓
[API] 校验 → 写入 scan 记录 (status=pending) → 入队 Redis
  │
  ↓
[Worker] 拉取任务 → 执行 Scanner.run()
  │  ├─ Phase 1: Connectivity Check
  │  ├─ Phase 2: Authenticity Probes (并发 ~30)
  │  ├─ Phase 3: Billing Audit
  │  ├─ Phase 4: Cache Audit (发两次，对比)
  │  ├─ Phase 5: QoS Profiling (采样 TTFT/ITL)
  │  └─ Phase 6: Privacy Canary
  │
  ↓
[Scoring Engine] 融合 → 生成 Report
  │
  ↓
[API] 更新 scan 记录 → 推送 SSE 事件给前端
  │
  ↓
[用户] 实时看到报告 + 可下载 PDF
```

## 关键设计原则

1. **Core 与 Delivery 严格解耦**：CLI 和 SaaS 共用同一套探针代码，修一处，两处受益
2. **探针可插拔**：`@register_probe` 装饰器注册，题库可热更新
3. **Provider 抽象**：所有供应商统一成 `ChatProvider` 接口，扫描逻辑与具体协议无关
4. **零状态 Worker**：Worker 可水平扩展，任务状态只在 Redis/DB
5. **API Key 最小化停留**：一次性扫描模式下 key 永不入库，只在 Worker 内存中驻留
