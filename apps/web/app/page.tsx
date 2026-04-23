export default function HomePage() {
  return (
    <div className="py-10 space-y-10">
      <section className="text-center space-y-4">
        <h1 className="text-4xl font-bold">
          你买的 <span className="text-brand">Opus / GPT / Gemini</span> 是真的吗？
        </h1>
        <p className="text-neutral-300 text-lg">
          15code Verify — 免费的 LLM API 服务商诚信度检测工具
        </p>
        <p className="text-neutral-400 text-sm">
          检测模型掺水 · token 虚报 · 缓存合规 · 性能衰减 · 隐私安全
        </p>
        <a
          href="/verify"
          className="inline-block bg-brand hover:bg-brand-dark text-white font-semibold px-6 py-3 rounded-lg"
        >
          立即开始检测 →
        </a>
        <p className="text-xs text-neutral-500">
          完全免费 · 扫描消耗的是你自己第三方渠道的额度 ·
          不消耗 15code 资源
        </p>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          ["🔍 真伪度", "指纹识别 + 风格计量 + 能力差分，推断实际模型身份"],
          ["💰 计费诚信", "官方 tokenizer 本地对账，发现 token 虚报"],
          ["🗄️ 缓存合规", "prompt cache 折扣是否兑现"],
          ["⚡ 性能质量", "TTFT / ITL / 可用性 / 智商衰减"],
          ["🔒 隐私安全", "canary token 追踪 · TLS 审计 · 网络路径"],
          ["📊 公开榜单", "社区匿名贡献 · 透明可质询"],
        ].map(([t, d]) => (
          <div key={t} className="p-4 border border-neutral-800 rounded-lg">
            <div className="font-semibold">{t}</div>
            <div className="text-sm text-neutral-400 mt-1">{d}</div>
          </div>
        ))}
      </section>

      <section className="p-6 border border-brand/40 rounded-lg bg-brand/5">
        <h3 className="font-semibold">来自 15code 的话</h3>
        <p className="text-sm text-neutral-300 mt-2">
          这个工具完全免费，由 <a href="https://15code.com" className="text-brand underline">15code</a> 开源维护。
          我们相信 LLM 生态需要更多透明度 —— 无论你最终用哪家服务，
          我们希望你拿到的是物有所值的产品。
          如果这个工具帮到了你，欢迎 <a href="https://github.com/15code/verify"
          className="underline">给 GitHub 加个 Star</a>，
          或者试试我们自家的服务 —— 我们用同样的标准要求自己。
        </p>
      </section>
    </div>
  );
}
