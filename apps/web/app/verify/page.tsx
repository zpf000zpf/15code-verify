"use client";
import { useState } from "react";

type Stage = { stage: string; progress: number };

export default function VerifyPage() {
  const [form, setForm] = useState({
    base_url: "",
    api_key: "",
    claimed_model: "",
    protocol: "openai",
    depth: "standard",
    publish_to_leaderboard: false,
    vendor_display_name: "",
    tos_accepted: false,
  });
  const [scanId, setScanId] = useState<string | null>(null);
  const [stage, setStage] = useState<Stage | null>(null);
  const [report, setReport] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  async function start(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setReport(null);
    setScanId(null);

    if (!form.tos_accepted) {
      setError("必须同意服务条款");
      return;
    }

    const res = await fetch(`${api}/v1/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    const data = await res.json();
    if (!res.ok) {
      setError(data.detail || "启动扫描失败");
      return;
    }
    setScanId(data.scan_id);

    // SSE progress
    const evt = new EventSource(`${api}/v1/scan/${data.scan_id}/events`);
    evt.addEventListener("progress", (e: any) => {
      try {
        const s = JSON.parse(e.data);
        setStage(s);
        if (s.stage === "done" || s.stage === "error") {
          evt.close();
          fetch(`${api}/v1/scan/${data.scan_id}`).then(r => r.json()).then(r => {
            if (r.report) setReport(r.report);
            if (r.error) setError(r.error);
          });
        }
      } catch {}
    });
  }

  return (
    <div className="py-8 space-y-6">
      <h1 className="text-2xl font-bold">开始检测</h1>

      {!report && (
        <form onSubmit={start} className="space-y-4 max-w-xl">
          <Field label="第三方 Base URL">
            <input required className="input"
              placeholder="https://api.some-reseller.com/v1"
              value={form.base_url}
              onChange={e => setForm({ ...form, base_url: e.target.value })} />
          </Field>
          <Field label="API Key">
            <input required type="password" className="input"
              placeholder="sk-xxxxxx"
              value={form.api_key}
              onChange={e => setForm({ ...form, api_key: e.target.value })} />
            <p className="text-xs text-neutral-500 mt-1">
              ⓘ 一次性扫描下，key 仅内存驻留，扫描结束即销毁，不落盘。
            </p>
          </Field>
          <Field label="声明模型">
            <input required className="input"
              placeholder="claude-opus-4-7"
              value={form.claimed_model}
              onChange={e => setForm({ ...form, claimed_model: e.target.value })} />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="协议">
              <select className="input" value={form.protocol}
                onChange={e => setForm({ ...form, protocol: e.target.value })}>
                <option value="openai">OpenAI 兼容</option>
                <option value="anthropic">Anthropic</option>
              </select>
            </Field>
            <Field label="档位">
              <select className="input" value={form.depth}
                onChange={e => setForm({ ...form, depth: e.target.value })}>
                <option value="quick">快速 (~30s)</option>
                <option value="standard">标准 (~3min)</option>
                <option value="deep">深度 (~10min)</option>
              </select>
            </Field>
          </div>

          <div className="border-t border-neutral-800 pt-4 space-y-2">
            <label className="flex items-start gap-2 text-sm">
              <input type="checkbox"
                checked={form.publish_to_leaderboard}
                onChange={e => setForm({ ...form, publish_to_leaderboard: e.target.checked })} />
              <span>
                匿名贡献数据到公开榜单
                <span className="block text-xs text-neutral-500">
                  勾选后本次扫描的聚合统计数据将进入匿名榜单，永久保留。
                  仅接受你主动授权的数据，符合 <a href="/docs/LEADERBOARD_POLICY" className="underline">榜单政策</a>。
                </span>
              </span>
            </label>
            {form.publish_to_leaderboard && (
              <Field label="供应商展示名（榜单显示）">
                <input className="input"
                  placeholder="e.g. Provider-A"
                  value={form.vendor_display_name}
                  onChange={e => setForm({ ...form, vendor_display_name: e.target.value })} />
              </Field>
            )}
            <label className="flex items-start gap-2 text-sm">
              <input required type="checkbox"
                checked={form.tos_accepted}
                onChange={e => setForm({ ...form, tos_accepted: e.target.checked })} />
              <span>
                我已阅读并同意 <a href="/docs/TERMS_OF_SERVICE" className="underline">服务条款</a>，
                并担保拥有测试该 API 端点的合法权限。
              </span>
            </label>
          </div>

          <button className="bg-brand hover:bg-brand-dark px-6 py-2 rounded font-semibold">
            开始扫描
          </button>
          <style>{`
            .input {
              width: 100%; padding: .5rem .75rem; border-radius: .375rem;
              background: #111; border: 1px solid #333; color: #eee;
            }
          `}</style>
        </form>
      )}

      {scanId && !report && (
        <div className="p-4 border border-neutral-800 rounded">
          <div>扫描 ID：<code>{scanId}</code></div>
          <div className="mt-2">进度：{stage?.stage ?? "starting"} ({((stage?.progress ?? 0)*100).toFixed(0)}%)</div>
        </div>
      )}

      {error && <div className="text-red-400">错误：{error}</div>}

      {report && <ReportView report={report} />}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="text-sm text-neutral-300 mb-1">{label}</div>
      {children}
    </label>
  );
}

function ReportView({ report }: { report: any }) {
  return (
    <div className="space-y-4">
      <div className="p-6 border border-neutral-800 rounded">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">扫描报告 · {report.scan_id}</h2>
          <div className="text-sm text-neutral-400">方法论 {report.methodology_version}</div>
        </div>
        <div className="text-3xl mt-2">
          信任分：<span className="text-brand">{report.trust_score}</span> / 100
          <span className="ml-3 text-base text-neutral-400">{report.verdict}</span>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
          {report.authenticity && (
            <Cell title="🔍 真伪度"
              body={`claimed 一致性 ${(report.authenticity.confidence_is_claimed*100).toFixed(0)}%` +
                    (report.authenticity.likely_model
                     ? ` · 最相似：${report.authenticity.likely_model}` : "")}/>
          )}
          {report.billing_audit && (
            <Cell title="💰 计费"
              body={`input 偏差 ${report.billing_audit.input_token_deviation_pct.toFixed(1)}% / ` +
                    `output 偏差 ${report.billing_audit.output_token_deviation_pct.toFixed(1)}%`}/>
          )}
          {report.cache_audit && (
            <Cell title="🗄️ 缓存"
              body={report.cache_audit.cache_supported ? "已观测到缓存支持" : "未观测到缓存"}/>
          )}
          {report.qos && (
            <Cell title="⚡ 性能"
              body={`TTFT p50: ${report.qos.ttft_ms_p50.toFixed(0)}ms · 错误率 ${(report.qos.error_rate*100).toFixed(0)}%`}/>
          )}
        </div>
        <p className="mt-6 text-xs italic text-neutral-500">{report.disclaimer}</p>
      </div>

      <div className="flex gap-2">
        <button className="border border-neutral-700 px-4 py-2 rounded"
          onClick={() => navigator.clipboard.writeText(JSON.stringify(report, null, 2))}>
          复制 JSON
        </button>
        <a className="border border-neutral-700 px-4 py-2 rounded"
           href={`data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(report, null, 2))}`}
           download={`${report.scan_id}.json`}>
          下载报告
        </a>
      </div>

      <div className="p-4 bg-brand/5 border border-brand/40 rounded text-sm">
        这个免费工具由 <a className="underline text-brand" href="https://15code.com">15code</a> 提供。
        如果帮到了你，欢迎把报告分享出去 —— 让更多人看到真实的 LLM 市场 ♥
      </div>
    </div>
  );
}

function Cell({ title, body }: { title: string; body: string }) {
  return (
    <div className="p-3 border border-neutral-800 rounded">
      <div className="font-semibold">{title}</div>
      <div className="text-neutral-300">{body}</div>
    </div>
  );
}
