# 探针设计原理（Probe Design）

**方法论版本：v1.0**

本文档公开 15code Verify 的检测方法论原理。  
**具体探针题库内容保密**，以防被中转商针对性路由绕过；方法论与评分算法完全公开。

---

## 一、核心哲学

- **多维度融合**：任何单一维度都可能被对抗，必须融合多源信号
- **统计语言**：永远输出"概率 / 置信度"，不输出"是 / 不是"
- **可证伪**：所有判断必须可以被供应商用数据反驳
- **保守优先**：不确定时返回"数据不足"，而不是错判

## 二、五大检测维度

### 2.1 真伪度（Authenticity）
由 N 个探针共同投票：

| 探针类型 | 原理 |
|---|---|
| **Tokenizer Fingerprint** | 不同模型家族用不同 tokenizer，回显特殊 Unicode 时的切分痕迹泄露身份 |
| **Self-Identification (侧信道)** | 不直接问"你是谁"。通过问"默认温度"、"训练数据截止"等侧信道获取隐式线索 |
| **Stylometry** | 温度=0 下采样多次生成，计算风格特征（长度 / markdown 率 / 列表偏好），与官方基线对比 |
| **Capability Diff** | 设置难度分层题，观察 "easy 能过 + hard 不过" → mini 特征 vs "全通过" → top-tier 特征 |

每个探针输出各候选模型的 log-score；所有 score 累加后做 softmax → 得到模型概率分布。

### 2.2 计费诚信（Billing Audit）
- 官方 tokenizer 本地计算 input/output token
- 对比供应商返回的 `usage.input_tokens` / `usage.output_tokens`
- 多组长度采样（短/中/长），求系统性偏差
- 注意：Claude 家族无公开 tokenizer，使用 `cl100k_base` 近似，结果标"估算"

### 2.3 缓存合规（Cache Compliance）
1. 发送带 `cache_control` 的长 prompt（首次）→ 检查 `cache_creation_input_tokens`
2. 2 秒后重发同样前缀 → 检查 `cache_read_input_tokens`
3. 若 creation 已计入但 read 为 0 → 供应商可能只收了创建费，没兑现读折扣
4. 预估多付费比例：按官方折扣公式反推

### 2.4 性能质量（QoS）
- TTFT / ITL / total latency 采样（N=5~20）
- 错误率
- 能力衰减：跑少量 MMLU / HumanEval 题，对比官方基线
- 量化嫌疑：输出困惑度异常 / 确定性任务的离散程度

### 2.5 隐私安全（Privacy）
- canary 字符串追踪（布设监控网络，观察 canary 是否出现在外部）
- TLS 版本 / 证书链核查
- DNS / traceroute 异常跳点

---

## 三、打分融合

```
authenticity_score ∈ [0, 1]  ← softmax(sum of probe log-scores)
billing_score      ∈ [0, 1]  ← exp(-|deviation%|/10)
cache_score        ∈ [0, 1]  ← 0.0 / 1.0 / 0.5
qos_score          ∈ [0, 1]  ← weighted by latency / error_rate / capability

trust_score_0_100 = 100
                  - (1 - authenticity_score) * 40
                  - (1 - billing_score)      * 25
                  - (1 - cache_score)        * 15
                  - (1 - qos_score)          * 20
```

---

## 四、抗对抗设计

- **私有题库**：题库本身不公开，仅公开算法与类别
- **题库轮换**：每月更新 ≥30% 的题目
- **流量伪装**：扫描器的 UA / 请求节奏模拟真实用户
- **分布式 IP**：探针流量来自多个地域住宅 IP（避免单一 IP 被识别）
- **混入真实流量**：可选 opt-in 让用户把自己的真实 prompt 混入探针流量

---

## 五、已知局限（透明公开）

1. 真伪度判断存在**不可消除的不确定性**，永远输出概率
2. 风格基线依赖 15code 自己维护的官方 API 访问，若官方模型升级会有短暂漂移
3. Claude 无公开 tokenizer，billing 对账是**估算**
4. 单次扫描样本量有限，建议对同一 endpoint 多次测试取均值

---

## 六、版本历史

| 版本 | 日期 | 更新内容 |
|---|---|---|
| v1.0 | 2026-04-23 | 首版发布 |

---

## 七、质疑渠道

如对方法论有任何质疑或改进建议：
- GitHub Issues: https://github.com/zpf000zpf/15code-verify/issues
- 邮件：methodology@15code.com

欢迎学术界与工业界共同完善。
