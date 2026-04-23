import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "15code Verify — LLM 服务商诚信度检测",
  description:
    "免费开源的 LLM API 服务商审计工具。检测模型掺水、token 虚报、缓存合规与性能衰减。由 15code 出品。",
  openGraph: {
    title: "15code Verify",
    description: "免费开源的 LLM API 诚信度检测工具 · 由 15code 出品",
    url: "https://verify.15code.com",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <header className="border-b border-neutral-800">
          <div className="mx-auto max-w-5xl flex items-center justify-between p-4">
            <a href="/" className="font-bold text-lg">
              <span className="text-brand">15code</span> Verify
            </a>
            <nav className="flex gap-4 text-sm text-neutral-300">
              <a href="/verify" className="hover:text-white">开始检测</a>
              <a href="/leaderboard" className="hover:text-white">榜单</a>
              <a href="/docs" className="hover:text-white">文档</a>
              <a href="https://15code.com"
                 target="_blank" rel="noreferrer"
                 className="hover:text-white text-brand">15code 主站 ↗</a>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-5xl p-6">{children}</main>
        <footer className="mt-16 border-t border-neutral-800">
          <div className="mx-auto max-w-5xl p-6 text-sm text-neutral-400">
            <div>
              本工具提供的数据反映特定时间点的技术指标观测，
              <b>不构成对服务商的法律评价或商业决策建议</b>。
              详见 <a href="/docs/LEADERBOARD_POLICY" className="underline">榜单政策</a> 与
              <a href="/docs/TERMS_OF_SERVICE" className="underline"> 服务条款</a>。
            </div>
            <div className="mt-2">
              © 2026 <a href="https://15code.com" className="text-brand">15code</a> ·
              <span className="ml-1">Apache 2.0 开源</span> ·
              <a href="https://github.com/15code/verify" className="ml-1 underline">GitHub</a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
