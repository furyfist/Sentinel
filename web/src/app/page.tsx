import Link from 'next/link'
import {
  ShieldCheck, Zap, GitBranch, TriangleAlert, Hand, Activity,
  MessageSquare, Network, CircuitBoard, Sparkles, Workflow,
  Siren, GitPullRequest, ChartLine, DollarSign, Boxes, CodeXml,
  Hash,
} from 'lucide-react'

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header />
      <Hero />
      <SourcesBar />
      <ProblemsSection />
      <HowItWorksSection />
      <FeaturesSection />
      <SourcesSection />
      <CtaSection />
      <Footer />
    </div>
  )
}

function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
        <div className="flex items-center gap-2">
          <div className="grid h-7 w-7 place-items-center rounded-md bg-foreground text-background">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <span className="text-sm font-semibold tracking-tight">Sentinel</span>
          <span className="ml-2 rounded border border-border bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-slate-500">
            v0.1 · Coral OSS
          </span>
        </div>
        <nav className="hidden items-center gap-7 text-sm text-slate-500 md:flex">
          <a href="#problems" className="hover:text-foreground transition-colors">Problems</a>
          <a href="#how" className="hover:text-foreground transition-colors">How it works</a>
          <a href="#features" className="hover:text-foreground transition-colors">Features</a>
          <a href="#sources" className="hover:text-foreground transition-colors">Sources</a>
        </nav>
        <div className="flex items-center gap-3">
          <a href="#" className="hidden text-sm text-slate-500 hover:text-foreground transition-colors sm:inline">Docs</a>
          <Link href="/dashboard" className="rounded-md bg-foreground px-3 py-1.5 text-sm font-medium text-background hover:opacity-90 transition-opacity">
            Get started
          </Link>
        </div>
      </div>
    </header>
  )
}

function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-border">
      <div className="absolute inset-0 bg-grid opacity-60 [mask-image:radial-gradient(ellipse_at_top,black,transparent_70%)]" />
      <div className="relative mx-auto max-w-7xl px-6 pb-20 pt-16 md:pt-24">
        <div className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-3 py-1 font-mono text-[11px] uppercase tracking-wider text-slate-500">
          <span className="h-1.5 w-1.5 rounded-full bg-success" />
          Pirates of the Coral-bean · Track 1: Enterprise Agent
        </div>
        <h1 className="mt-6 max-w-4xl text-4xl font-bold leading-[1.05] tracking-tight md:text-6xl">
          Your AI agents are silently burning money
          <span className="text-slate-400"> and breaking production.</span>
        </h1>
        <p className="mt-6 max-w-2xl text-base text-slate-500 md:text-lg">
          Sentinel cross-queries 7 observability sources via Coral SQL to detect, diagnose, and govern AI system failures — and routes high-risk actions through human approval before acting.
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-3">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-md bg-foreground px-4 py-2.5 text-sm font-medium text-background hover:opacity-90 transition-opacity"
          >
            Deploy Sentinel <Zap className="h-4 w-4" />
          </Link>
          <a href="#how" className="inline-flex items-center gap-2 rounded-md border border-border bg-background px-4 py-2.5 text-sm font-medium text-foreground hover:bg-slate-50 transition-colors">
            See how it works
          </a>
          <span className="font-mono text-xs text-slate-400">$ coral query --join langfuse,sentry,github,slack</span>
        </div>

        <div className="mt-12 grid gap-4 md:grid-cols-3">
          <div className="md:col-span-2 rounded-lg border border-border bg-white shadow-sm overflow-hidden">
            <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
              <div className="flex items-center gap-1.5 font-mono text-xs text-slate-400">
                <span className="h-2.5 w-2.5 rounded-full bg-alert" />
                <span className="h-2.5 w-2.5 rounded-full bg-warning" />
                <span className="h-2.5 w-2.5 rounded-full bg-success" />
                <span className="ml-2">incident-2418.sql</span>
              </div>
              <span className="rounded border border-alert/30 bg-alert/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-alert">
                Loop detected
              </span>
            </div>
            <pre className="overflow-x-auto bg-slate-50/50 px-5 py-5 font-mono text-[12.5px] leading-relaxed text-slate-800 text-sm">
{`SELECT  l.trace_id, l.cost_usd, s.title AS error,
        g.sha, g.author, m.text AS slack_msg
FROM    langfuse.traces  l
JOIN    sentry.issues    s USING (trace_id)
JOIN    github.commits   g ON g.ts BETWEEN l.ts - '15m' AND l.ts
LEFT JOIN slack.messages m ON m.ts BETWEEN l.ts - '10m' AND l.ts + '10m'
WHERE   l.cost_usd > 50
  AND   l.retry_depth >= 4
ORDER BY l.cost_usd DESC;`}
            </pre>
            <div className="border-t border-border bg-slate-50 px-5 py-3 text-xs text-slate-500">
              <span className="font-mono font-medium text-foreground">7 rows</span> · cross-source JOIN across Langfuse, Sentry, GitHub, Slack · 412ms
            </div>
          </div>

          <div className="space-y-3">
            <MetricCard label="Loop cost (last 1h)" value="$284.10" sub="+412%" icon={<DollarSign className="h-3.5 w-3.5" />} accent="alert" />
            <MetricCard label="Sampling efficiency" value="84.6%" sub="-15.4% volume" icon={<Activity className="h-3.5 w-3.5" />} accent="success" />
            <MetricCard label="Pending approvals" value="3" sub="2 expire <10m" icon={<Hand className="h-3.5 w-3.5" />} accent="info" />
          </div>
        </div>
      </div>
    </section>
  )
}

function MetricCard({ label, value, sub, icon, accent }: {
  label: string; value: string; sub: string
  icon: React.ReactNode; accent: 'alert' | 'success' | 'info'
}) {
  const colors: Record<string, string> = {
    alert: 'bg-alert/10 text-alert border-alert/20',
    success: 'bg-success/10 text-success border-success/20',
    info: 'bg-info/10 text-info border-info/20',
  }
  return (
    <div className="rounded-lg border border-border bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500">{label}</span>
        <span className={`grid h-7 w-7 place-items-center rounded border ${colors[accent]}`}>{icon}</span>
      </div>
      <div className="mt-2 font-mono text-2xl font-semibold tracking-tight">{value}</div>
      <div className="mt-1 text-xs text-slate-400">{sub}</div>
    </div>
  )
}

function SourcesBar() {
  const sources = [
    { name: 'Langfuse', color: 'text-info', badge: 'Custom Coral source' },
    { name: 'Sentry', color: 'text-alert', badge: null },
    { name: 'GitHub', color: 'text-foreground', badge: null },
    { name: 'Slack', color: 'text-success', badge: null },
    { name: 'Datadog', color: 'text-info', badge: null },
    { name: 'PagerDuty', color: 'text-alert', badge: null },
    { name: 'Linear', color: 'text-info', badge: null },
  ]
  return (
    <section className="border-b border-border bg-slate-50/80">
      <div className="mx-auto max-w-7xl px-6 py-5">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-3 text-sm">
          <span className="font-mono text-[11px] uppercase tracking-wider text-slate-400">Sources joined via Coral SQL</span>
          {sources.map((s) => (
            <span key={s.name} className="inline-flex items-center gap-2 rounded-full border border-border bg-white px-3 py-1 shadow-sm">
              <span className={`h-1.5 w-1.5 rounded-full bg-current ${s.color}`} />
              <span className="text-sm font-medium text-foreground">{s.name}</span>
              {s.badge && (
                <span className="font-mono text-[9px] uppercase tracking-wider text-slate-400">{s.badge}</span>
              )}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}

function ProblemsSection() {
  const problems = [
    {
      icon: <DollarSign className="h-4 w-4" />,
      accent: 'alert' as const,
      label: 'Problem 01',
      title: 'Agent loop cost explosions',
      desc: 'Multi-agent retry loops burn hundreds of dollars before anyone notices. Sentinel detects loop patterns in Langfuse traces, fires a kill signal, and posts an interactive Slack alert with a Kill button.',
    },
    {
      icon: <GitBranch className="h-4 w-4" />,
      accent: 'warning' as const,
      label: 'Problem 02',
      title: 'Prompt drift & fragility',
      desc: 'Minor prompt edits silently break downstream JSON parsing. Sentinel maintains schema snapshots per feature, validates every trace, and blames the exact GitHub commit that caused the regression.',
    },
    {
      icon: <TriangleAlert className="h-4 w-4" />,
      accent: 'alert' as const,
      label: 'Problem 03',
      title: 'Silent tool call failures',
      desc: 'Tools return 200 OK with semantically wrong output. Sentinel cross-references tool outputs against Sentry errors in the same trace window to surface failures that look like successes.',
    },
    {
      icon: <Hand className="h-4 w-4" />,
      accent: 'info' as const,
      label: 'Problem 04',
      title: 'No human-in-the-loop governance',
      desc: 'Agents execute high-risk actions without checkpoints. Sentinel routes anomalies through an approval gate — Slack buttons or a web queue, full audit trail, state written back.',
    },
    {
      icon: <Activity className="h-4 w-4" />,
      accent: 'success' as const,
      label: 'Problem 05',
      title: 'Telemetry data saturation',
      desc: 'AI systems generate overwhelming trace volume. Sentinel scores every trace and drops routine noise — ~85% volume reduction while retaining 100% of actionable data.',
    },
    {
      icon: <MessageSquare className="h-4 w-4" />,
      accent: 'dark' as const,
      label: 'The Slack JOIN',
      title: 'Social context, fused via SQL.',
      desc: 'Every detection JOINs slack.messages on the incident window — surfacing what the team was saying during the event. No other observability tool fuses social and technical signal this way.',
    },
  ]

  return (
    <section id="problems" className="border-b border-border">
      <div className="mx-auto max-w-7xl px-6 py-20">
        <div className="max-w-3xl">
          <div className="font-mono text-[11px] uppercase tracking-wider text-info">The five problems</div>
          <h2 className="mt-3 text-3xl font-bold tracking-tight md:text-4xl">
            Production AI fails in ways your existing tooling can't see.
          </h2>
          <p className="mt-3 text-base text-slate-500">
            Logs, metrics, and traces in isolation miss the cross-source patterns that actually cause incidents.
          </p>
        </div>
        <div className="mt-12 grid gap-px overflow-hidden rounded-xl border border-border bg-border md:grid-cols-2 lg:grid-cols-3">
          {problems.map((p) => (
            <ProblemCard key={p.label} {...p} />
          ))}
        </div>
      </div>
    </section>
  )
}

type Accent = 'alert' | 'warning' | 'info' | 'success' | 'dark'

function ProblemCard({ icon, accent, label, title, desc }: {
  icon: React.ReactNode; accent: Accent; label: string; title: string; desc: string
}) {
  const iconColors: Record<Accent, string> = {
    alert: 'bg-alert/10 text-alert border-alert/20',
    warning: 'bg-amber-50 text-amber-700 border-amber-200',
    info: 'bg-info/10 text-info border-info/20',
    success: 'bg-success/10 text-success border-success/20',
    dark: 'bg-foreground text-background border-foreground',
  }
  return (
    <div className="bg-white p-6 transition-colors hover:bg-slate-50/60">
      <div className="flex items-center gap-3">
        <span className={`grid h-9 w-9 shrink-0 place-items-center rounded border ${iconColors[accent]}`}>{icon}</span>
        <span className="font-mono text-[11px] uppercase tracking-wider text-slate-400">{label}</span>
      </div>
      <h3 className="mt-4 text-base font-semibold tracking-tight">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-slate-500">{desc}</p>
    </div>
  )
}

function HowItWorksSection() {
  const modes = [
    {
      num: '01',
      icon: <Siren className="h-4 w-4 text-slate-400" />,
      title: 'On-Call Brain',
      trigger: 'Trigger: Datadog/Sentry spike or PagerDuty incident',
      desc: 'JOINs commits + errors + costs + Slack chatter. Claude writes a root-cause analysis, opens a GitHub issue, posts the summary to Slack.',
    },
    {
      num: '02',
      icon: <GitPullRequest className="h-4 w-4 text-slate-400" />,
      title: 'PR Risk Scorer',
      trigger: 'Trigger: GitHub pull_request opened',
      desc: 'Scores based on historical correlation of touched files to past cost and error regressions. Posts the risk score as a PR comment. Requests changes when risk > 70.',
    },
    {
      num: '03',
      icon: <ChartLine className="h-4 w-4 text-slate-400" />,
      title: 'Weekly Digest',
      trigger: 'Trigger: Monday 09:00 cron',
      desc: 'JOINs merged PRs + error-rate changes + Langfuse cost trends + Slack thread context. Output: What shipped · What broke · What to watch.',
    },
  ]
  const steps = [
    { num: '01', title: 'Detect', desc: 'Anomaly fires from cron, webhook, or threshold.' },
    { num: '02', title: 'JOIN', desc: 'Coral SQL fuses signal across 7 sources.' },
    { num: '03', title: 'Narrate', desc: 'Claude writes RCA, risk score, or digest.' },
    { num: '04', title: 'Govern', desc: 'High-risk action waits for human approval.' },
  ]
  return (
    <section id="how" className="border-b border-border bg-slate-50/80">
      <div className="mx-auto max-w-7xl px-6 py-20">
        <div className="max-w-3xl">
          <div className="font-mono text-[11px] uppercase tracking-wider text-info">How it works</div>
          <h2 className="mt-3 text-3xl font-bold tracking-tight md:text-4xl">
            Three activation modes. One agent. Seven sources.
          </h2>
          <p className="mt-3 text-base text-slate-500">
            Each mode runs cross-source SQL, lets Claude narrate the finding, and routes risky actions through human approval.
          </p>
        </div>
        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {modes.map((m) => (
            <div key={m.num} className="relative rounded-xl border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[11px] tracking-wider text-slate-400">MODE {m.num}</span>
                {m.icon}
              </div>
              <h3 className="mt-4 text-base font-semibold tracking-tight">{m.title}</h3>
              <p className="mt-1 font-mono text-[11px] text-info">{m.trigger}</p>
              <p className="mt-3 text-sm leading-relaxed text-slate-500">{m.desc}</p>
            </div>
          ))}
        </div>
        <div className="mt-6 grid gap-6 rounded-xl border border-border bg-white px-8 py-6 md:grid-cols-4">
          {steps.map((s) => (
            <div key={s.num} className="border-l-2 border-foreground pl-4">
              <div className="font-mono text-[11px] tracking-wider text-slate-400">STEP {s.num}</div>
              <div className="mt-1 text-sm font-semibold">{s.title}</div>
              <div className="mt-1 text-xs leading-relaxed text-slate-500">{s.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function FeaturesSection() {
  const features = [
    {
      icon: <Network className="h-4 w-4" />,
      title: 'Cross-source SQL',
      desc: "Coral SQL JOINs across 7 sources — the only way to ask 'what did the team say while costs spiked after this commit?'",
    },
    {
      icon: <CircuitBoard className="h-4 w-4" />,
      title: 'Forensics graph',
      desc: 'React Flow dependency graph: commits → errors → cost spikes → Slack messages. Causal chains for any window.',
    },
    {
      icon: <ShieldCheck className="h-4 w-4" />,
      title: 'HITL approval gate',
      desc: 'Interactive Slack Block Kit (HMAC-verified) and a web approval queue with full audit trail.',
    },
    {
      icon: <Sparkles className="h-4 w-4" />,
      title: 'Schema drift detection',
      desc: 'Per-feature output snapshots, validated on every trace. Drift events blame the commit.',
    },
    {
      icon: <Zap className="h-4 w-4" />,
      title: 'Loop kill switch',
      desc: 'Detects retry-loop signatures in Langfuse. One Slack button stops the bleeding before the bill arrives.',
    },
    {
      icon: <Workflow className="h-4 w-4" />,
      title: 'Smart sampling',
      desc: 'Scores every trace — errors, cost spikes, novel patterns kept; routine noise dropped. ~85% volume reduction.',
    },
  ]
  return (
    <section id="features" className="border-b border-border">
      <div className="mx-auto max-w-7xl px-6 py-20">
        <div className="max-w-3xl">
          <div className="font-mono text-[11px] uppercase tracking-wider text-info">The web command center</div>
          <h2 className="mt-3 text-3xl font-bold tracking-tight md:text-4xl">
            Dashboard · Incidents · Forensics · Risk · Quality · Approvals · Digest · Settings
          </h2>
          <p className="mt-3 text-base text-slate-500">
            Next.js + FastAPI, deployed on Vercel and Railway. React Flow forensics graph. Slack Block Kit write-back, HMAC verified.
          </p>
        </div>
        <div className="mt-12 grid gap-px overflow-hidden rounded-xl border border-border bg-border md:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div key={f.title} className="group bg-white p-6 transition-colors hover:bg-slate-50/80">
              <span className="grid h-9 w-9 place-items-center rounded border border-slate-200 bg-white text-info shadow-sm">
                {f.icon}
              </span>
              <h3 className="mt-4 text-base font-semibold tracking-tight">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-500">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function SourcesSection() {
  const sources = [
    { name: 'Langfuse', color: 'text-info', desc: 'Traces · Generations · Scores', badge: 'Custom Coral source' },
    { name: 'Sentry', color: 'text-alert', desc: 'Issues · Events · Errors', badge: null },
    { name: 'GitHub', color: 'text-foreground', desc: 'Commits · PRs · File diffs', badge: null },
    { name: 'Slack', color: 'text-success', desc: 'Messages · Threads · Channels', badge: null },
    { name: 'Datadog', color: 'text-info', desc: 'Monitors · Metrics · Events', badge: null },
    { name: 'PagerDuty', color: 'text-alert', desc: 'Incidents · Urgency · Timelines', badge: null },
    { name: 'Linear', color: 'text-info', desc: 'Issues · Sprints · Assignees', badge: null },
  ]
  return (
    <section id="sources" className="border-b border-border bg-slate-50/80">
      <div className="mx-auto max-w-7xl px-6 py-20">
        <div className="max-w-3xl">
          <div className="font-mono text-[11px] uppercase tracking-wider text-info">Seven sources, one query plane</div>
          <h2 className="mt-3 text-3xl font-bold tracking-tight md:text-4xl">All routed through Coral SQL.</h2>
          <p className="mt-3 text-base text-slate-500">
            The Langfuse spec is an original contribution — first community Langfuse source for Coral. Basic Auth + page-number pagination, 4 tables.
          </p>
        </div>
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {sources.map((s) => (
            <div key={s.name} className="rounded-xl border border-border bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Boxes className={`h-4 w-4 ${s.color}`} />
                  <span className="text-sm font-semibold">{s.name}</span>
                </div>
                <span className="font-mono text-[10px] uppercase tracking-wider text-slate-400">source</span>
              </div>
              <p className="mt-3 text-xs text-slate-500">{s.desc}</p>
              {s.badge && (
                <span className="mt-3 inline-block rounded border border-info/20 bg-info/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-info">
                  {s.badge}
                </span>
              )}
            </div>
          ))}
          <div className="rounded-xl border border-dashed border-slate-300 bg-white p-5 shadow-sm">
            <div className="flex items-center gap-2">
              <CodeXml className="h-4 w-4 text-slate-400" />
              <span className="text-sm font-semibold">Add your own</span>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-slate-500">Coral source specs are pluggable. Drop one in, JOIN it with the rest.</p>
          </div>
        </div>
      </div>
    </section>
  )
}

function CtaSection() {
  return (
    <section id="cta" className="border-b border-border">
      <div className="mx-auto max-w-7xl px-6 py-20">
        <div className="relative overflow-hidden rounded-xl border border-border bg-foreground text-background">
          <div className="absolute inset-0 bg-dots opacity-10" />
          <div className="relative grid gap-8 p-10 md:grid-cols-[1.4fr_1fr] md:items-center md:p-14">
            <div>
              <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
                Stop diagnosing AI failures one dashboard at a time.
              </h2>
              <p className="mt-4 max-w-xl text-sm leading-relaxed text-background/70 md:text-base">
                Sentinel runs in your stack, joins the signal your team already produces, and asks before it acts. Built for the Pirates of the Coral-bean hackathon by WeMakeDevs × Coral OSS.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <Link
                  href="/dashboard"
                  className="rounded-md bg-background px-4 py-2.5 text-sm font-medium text-foreground hover:opacity-90 transition-opacity"
                >
                  Deploy on Railway + Vercel
                </Link>
                <a href="#" className="inline-flex items-center gap-2 rounded-md border border-background/30 px-4 py-2.5 text-sm font-medium text-background transition-colors hover:bg-background/10">
                  <Hash className="h-4 w-4" /> Install Slack app
                </a>
              </div>
            </div>
            <div className="rounded-lg border border-background/15 bg-background/5 p-5 font-mono text-xs leading-relaxed">
              <div className="text-background/50"># 60-second install</div>
              <div className="mt-3 space-y-0.5 text-background">
                <div><span className="text-success">$</span> pip install sentinel-agent</div>
                <div><span className="text-success">$</span> sentinel init --sources \</div>
                <div className="pl-4 text-background/70">langfuse,sentry,github,slack,\</div>
                <div className="pl-4 text-background/70">datadog,pagerduty,linear</div>
                <div><span className="text-success">$</span> sentinel run --mode on-call</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="bg-background border-t border-border">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-8 text-xs text-slate-400 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-2">
          <div className="grid h-5 w-5 place-items-center rounded bg-foreground text-background">
            <ShieldCheck className="h-3 w-3" />
          </div>
          <span className="font-semibold text-foreground">Sentinel</span>
          <span>· AI Observability Agent</span>
        </div>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
          <span className="font-mono uppercase tracking-wider">Built for Coral OSS</span>
          <a href="https://github.com/Himanshu-Parangat/sentinel" className="hover:text-foreground transition-colors">GitHub</a>
          <a href="#" className="hover:text-foreground transition-colors">Docs</a>
          <a href="#" className="hover:text-foreground transition-colors">Hackathon entry</a>
        </div>
      </div>
    </footer>
  )
}
