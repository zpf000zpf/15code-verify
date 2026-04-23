export const metadata = {
  title: "下载 15code Verify · 命令行 / Docker / Python SDK",
  description: "免费开源的 LLM 服务商诚信度检测工具。多平台支持，一键下载。",
};

export default function DownloadPage() {
  return (
    <div className="py-10 space-y-10">
      <header className="text-center space-y-3">
        <h1 className="text-4xl font-bold">下载 15code Verify</h1>
        <p className="text-neutral-300">
          把检测工具带回家 —— 命令行、Docker、SDK，任选一种
        </p>
        <p className="text-xs text-neutral-500">
          完全免费 · Apache 2.0 开源 · 由 <a href="https://15code.com" className="text-brand">15code</a> 维护
        </p>
      </header>

      {/* PyPI / Pip */}
      <section className="p-6 border border-neutral-800 rounded-lg space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">🐍 pip 安装（推荐）</h2>
          <span className="text-xs bg-brand/20 text-brand px-2 py-1 rounded">最流行</span>
        </div>
        <p className="text-sm text-neutral-400">
          需要 Python 3.10+。安装后可直接使用 <code>verify</code> 命令。
        </p>
        <CodeBlock>
{`pip install 15code-verify

verify scan \\
  --base-url https://api.some-reseller.com/v1 \\
  --api-key sk-xxxxxx \\
  --claimed-model claude-opus-4-7`}
        </CodeBlock>
        <div className="flex gap-3 text-sm">
          <a className="text-brand underline" href="https://pypi.org/project/15code-verify/">PyPI 页面 ↗</a>
          <a className="text-brand underline" href="/docs/CLI">CLI 文档</a>
        </div>
      </section>

      {/* Docker */}
      <section className="p-6 border border-neutral-800 rounded-lg space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">🐳 Docker 自托管</h2>
          <span className="text-xs bg-brand/20 text-brand px-2 py-1 rounded">企业推荐</span>
        </div>
        <p className="text-sm text-neutral-400">
          适合内网 / 数据敏感场景。一键启动 Web + API。
        </p>
        <CodeBlock>
{`# 方式一：拉取官方镜像
docker run -d -p 3000:3000 -p 8000:8000 \\
  --name 15code-verify \\
  ghcr.io/15code/verify:latest

# 方式二：使用 docker-compose
curl -O https://verify.15code.com/download/docker-compose.yml
docker compose up -d

# 打开 http://localhost:3000`}
        </CodeBlock>
        <div className="flex gap-3 text-sm">
          <a className="text-brand underline" href="https://github.com/15code/verify/pkgs/container/verify">镜像仓库 ↗</a>
          <a className="text-brand underline" href="/download/docker-compose.yml">下载 docker-compose.yml</a>
        </div>
      </section>

      {/* Source tarball / GitHub */}
      <section className="p-6 border border-neutral-800 rounded-lg space-y-3">
        <h2 className="text-xl font-bold">📦 源码 / 离线安装包</h2>
        <p className="text-sm text-neutral-400">
          适合离线环境 / 二次开发 / 做 PR。
        </p>
        <div className="grid md:grid-cols-2 gap-3 text-sm">
          <a className="block p-3 border border-neutral-800 rounded hover:border-brand"
             href="https://github.com/15code/verify/archive/refs/heads/main.tar.gz">
            <div className="font-semibold">📥 完整源码（tar.gz）</div>
            <div className="text-neutral-400 mt-1">最新 main 分支打包</div>
          </a>
          <a className="block p-3 border border-neutral-800 rounded hover:border-brand"
             href="https://github.com/15code/verify/releases">
            <div className="font-semibold">🏷️ Releases（稳定版）</div>
            <div className="text-neutral-400 mt-1">签名的 release tarball + wheel</div>
          </a>
          <a className="block p-3 border border-neutral-800 rounded hover:border-brand"
             href="https://github.com/15code/verify.git">
            <div className="font-semibold">🔧 git clone</div>
            <div className="text-neutral-400 mt-1">git clone 后 ./scripts/setup.sh</div>
          </a>
          <a className="block p-3 border border-neutral-800 rounded hover:border-brand"
             href="/download/verify-cli-linux-x64">
            <div className="font-semibold">🐧 Linux x64 二进制</div>
            <div className="text-neutral-400 mt-1">单文件，无需 Python（PyInstaller 打包）</div>
          </a>
        </div>
      </section>

      {/* SDK */}
      <section className="p-6 border border-neutral-800 rounded-lg space-y-3">
        <h2 className="text-xl font-bold">🔌 Python SDK</h2>
        <p className="text-sm text-neutral-400">
          嵌入你自己的监控系统 / 采购流程。
        </p>
        <CodeBlock>
{`from verify_core import Scanner, ScanConfig

scanner = Scanner(ScanConfig(
    base_url="https://api.some-reseller.com/v1",
    api_key="sk-xxx",
    claimed_model="claude-opus-4-7",
    tos_accepted=True,
))
report = scanner.run()
print(report.trust_score)  # 0-100
print(report.authenticity.likely_model)`}
        </CodeBlock>
      </section>

      {/* REST API */}
      <section className="p-6 border border-neutral-800 rounded-lg space-y-3">
        <h2 className="text-xl font-bold">🌐 托管 REST API（在线服务）</h2>
        <p className="text-sm text-neutral-400">
          不想装任何东西？直接调我们的免费 API。
        </p>
        <CodeBlock>
{`curl -X POST https://verify.15code.com/v1/scan \\
  -H "Content-Type: application/json" \\
  -d '{
    "base_url": "https://api.some-reseller.com/v1",
    "api_key": "sk-xxxxxx",
    "claimed_model": "claude-opus-4-7",
    "tos_accepted": true
  }'`}
        </CodeBlock>
        <a className="text-brand underline text-sm" href="/docs/API">完整 API 文档 →</a>
      </section>

      {/* 15code ad banner (critical) */}
      <section className="p-6 border-2 border-brand/60 rounded-lg bg-brand/10 text-center space-y-3">
        <h3 className="text-xl font-bold">💡 来自 15code</h3>
        <p className="text-neutral-200">
          我们开源这个工具，是因为相信<b>透明的市场对所有人都好</b>。
        </p>
        <p className="text-neutral-300 text-sm">
          如果你正在找一个<b>不掺水、不虚报、价格透明</b>的 LLM API 网关 ——
          15code 提供统一接入 Claude / GPT / Gemini / DeepSeek 的服务，
          <b>按官方价计费，零套路</b>。我们自家服务也在本工具的公开榜单上受监督。
        </p>
        <div className="flex gap-3 justify-center pt-2">
          <a href="https://15code.com" className="bg-brand hover:bg-brand-dark px-6 py-2 rounded font-semibold">
            访问 15code 主站
          </a>
          <a href="https://15code.com/pricing" className="border border-brand text-brand px-6 py-2 rounded font-semibold hover:bg-brand/10">
            查看定价
          </a>
        </div>
      </section>

      {/* Install verification */}
      <section className="p-6 border border-neutral-800 rounded-lg space-y-3">
        <h2 className="text-xl font-bold">✅ 验证安装</h2>
        <CodeBlock>
{`verify version
# 输出：
#   15code Verify
#     verify-cli  0.1.0
#     verify-core 0.1.0
#     by 15code · https://15code.com

verify about     # 查看更多 15code 相关链接`}
        </CodeBlock>
      </section>
    </div>
  );
}

function CodeBlock({ children }: { children: React.ReactNode }) {
  return (
    <pre className="bg-black/50 border border-neutral-800 rounded p-4 text-sm overflow-x-auto">
      <code>{children}</code>
    </pre>
  );
}
