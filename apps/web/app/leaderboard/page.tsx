export default function LeaderboardPage() {
  return (
    <div className="py-10 space-y-6">
      <h1 className="text-2xl font-bold">公开榜单（Phase 1）</h1>
      <div className="p-4 border border-yellow-500/40 bg-yellow-500/5 rounded text-sm">
        ⓘ 榜单目前处于 <b>数据积累阶段</b>。
        公开展示将在积累足够匿名授权样本后启动。
        详见 <a href="/docs/LEADERBOARD_POLICY" className="underline">榜单政策</a>。
      </div>
      <div className="text-neutral-400 text-sm">
        <p><b>榜单原则：</b></p>
        <ul className="list-disc ml-5 mt-2 space-y-1">
          <li>仅聚合用户主动勾选"允许贡献"的扫描数据</li>
          <li>单供应商样本 &lt; 100 不展示</li>
          <li>所有指标以 <code>均值 ± 置信区间</code> 展示</li>
          <li>使用中立技术语言，不作商业评价</li>
          <li>供应商可通过 dispute@15code.com 申辩</li>
        </ul>
      </div>
    </div>
  );
}
