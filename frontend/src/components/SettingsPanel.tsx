import { useState } from "react";
import type { Session } from "../auth.ts";
import { initials } from "./AccountMenu.tsx";
import {
  IconArrowDown,
  IconArrowUp,
  IconChat,
  IconChevronLeft,
  IconClock,
  IconCoin,
  IconLevel,
  IconSparkle,
  IconUser,
} from "./icons.tsx";

interface SettingsPanelProps {
  session: Session;
}

type SettingsTab = "account" | "usage";

// Placeholder figures below -- Agno already records per-run input/output
// tokens in tmp/educa_agent.db, but those rows aren't scoped to a user and
// there's no pricing table yet, so nothing real can be aggregated here
// until that pipeline exists (see backend/app/agents/team.py).
const USAGE_CHART = [46, 40, 54, 48, 62, 58, 26, 32, 20, 38, 14, 30, 22, 6].map((h) => 84 - h);
const FEATURE_LIMITS = [
  { name: "Syllabus generation", used: "182.4K", limit: "300K", pct: 61, color: "var(--accent)" },
  { name: "Lesson chat", used: "96.7K", limit: "150K", pct: 64, color: "var(--violet)" },
  { name: "Quiz grading", used: "41.2K", limit: "100K", pct: 41, color: "var(--orange)" },
];
const COST_ROWS = [
  { name: "Syllabus generation", value: "$9.80", color: "var(--accent)" },
  { name: "Lesson chat", value: "$6.15", color: "var(--violet)" },
  { name: "Quiz grading", value: "$2.47", color: "var(--orange)" },
];
const ACTIVITY_LOG = [
  { time: "9:42 AM", feature: "Lesson chat", model: "Sonnet 5", tokens: "1,240", cost: "$0.06", color: "var(--violet)" },
  { time: "9:15 AM", feature: "Syllabus gen.", model: "Sonnet 5", tokens: "8,960", cost: "$0.41", color: "var(--accent)" },
  { time: "Yesterday", feature: "Quiz grading", model: "Haiku 4.5", tokens: "3,100", cost: "$0.04", color: "var(--orange)" },
  { time: "Yesterday", feature: "Lesson chat", model: "Sonnet 5", tokens: "2,050", cost: "$0.10", color: "var(--violet)" },
];

export default function SettingsPanel({ session }: SettingsPanelProps) {
  const [tab, setTab] = useState<SettingsTab>("account");
  const [navExpanded, setNavExpanded] = useState(true);

  return (
    <div className="settings-page">
      <nav className={`settings-nav${navExpanded ? "" : " is-collapsed"}`}>
        <div className="settings-nav-items">
          <h1>Settings</h1>
          <button
            type="button"
            className={`settings-nav-btn${tab === "account" ? " is-active" : ""}`}
            title="Account"
            onClick={() => setTab("account")}
          >
            <IconUser />
            <span className="settings-nav-label">Account</span>
          </button>
          <button
            type="button"
            className={`settings-nav-btn${tab === "usage" ? " is-active" : ""}`}
            title="AI usage & limits"
            onClick={() => setTab("usage")}
          >
            <IconLevel />
            <span className="settings-nav-label">AI usage &amp; limits</span>
          </button>
        </div>
        <button
          type="button"
          className="settings-nav-toggle"
          title={navExpanded ? "Collapse settings navigation" : "Expand settings navigation"}
          aria-label={navExpanded ? "Collapse settings navigation" : "Expand settings navigation"}
          onClick={() => setNavExpanded((v) => !v)}
        >
          <IconChevronLeft className="settings-nav-toggle-icon" />
        </button>
      </nav>

      <div className="settings-content">
        {tab === "account" ? <AccountTab session={session} /> : <UsageTab />}
      </div>
    </div>
  );
}

function AccountTab({ session }: { session: Session }) {
  const roleLabel = session.user.role === "teacher" ? "Teacher" : "Student";
  return (
    <div className="settings-stack">
      <div className="settings-content-head">
        <h2>Account</h2>
        <p>Your Educa Studio profile.</p>
      </div>
      <div className="settings-card">
        <div className="account-profile">
          <div className="account-profile-avatar">{initials(session.user.name)}</div>
          <div className="account-profile-main">
            <div className="account-profile-name">{session.user.name}</div>
            <div className="account-profile-email">{session.user.email}</div>
          </div>
        </div>
        <div className="account-plan-row">
          <span>{roleLabel} account</span>
          <span className="plan-pill">Free · early access</span>
        </div>
      </div>
    </div>
  );
}

function UsageTab() {
  return (
    <div className="settings-stack">
      <div className="settings-content-head">
        <h2>AI usage &amp; limits</h2>
        <p>Track how Studio's AI assistant uses your Anthropic account each billing cycle.</p>
      </div>

      <div className="settings-card model-card">
        <div className="model-badge">
          <IconSparkle />
        </div>
        <div className="model-card-main">
          <div className="model-card-title">Powered by Claude Sonnet 5</div>
          <div className="model-card-sub">
            Handles syllabus drafts, lesson chat, and quiz grading across Studio, via your Anthropic account.
          </div>
        </div>
        <div className="model-tag">claude-sonnet-5</div>
      </div>

      <div className="settings-row-3">
        <div className="settings-card">
          <div className="stat-tile-label"><IconArrowDown />Tokens in</div>
          <div className="stat-value">428.3K</div>
          <div className="stat-delta">this cycle</div>
        </div>
        <div className="settings-card">
          <div className="stat-tile-label"><IconArrowUp />Tokens out</div>
          <div className="stat-value">96.7K</div>
          <div className="stat-delta">this cycle</div>
        </div>
        <div className="settings-card">
          <div className="stat-tile-label"><IconChat />Requests</div>
          <div className="stat-value">1,204</div>
          <div className="stat-delta">this cycle</div>
        </div>
      </div>

      <div className="settings-row-2">
        <div className="settings-card">
          <div className="settings-card-title">Usage trend, last 14 days</div>
          <div className="chart-total">
            <span className="chart-total-value">525.0K</span>
            <span className="chart-total-label">total tokens</span>
          </div>
          <svg viewBox="0 0 300 84" width="100%" height="84" preserveAspectRatio="none">
            {USAGE_CHART.map((y, i) => (
              <rect
                key={i}
                x={i * 20}
                y={y}
                width="14"
                height={84 - y}
                rx="2"
                fill="var(--accent)"
                opacity={i >= USAGE_CHART.length - 4 ? 1 : 0.55}
              />
            ))}
          </svg>
          <div className="chart-range">
            <span>14 days ago</span>
            <span>today</span>
          </div>
        </div>

        <div className="settings-card">
          <div className="settings-card-title">Plan caps by feature</div>
          {FEATURE_LIMITS.map((f) => (
            <div className="meter-row" key={f.name}>
              <div className="meter-head">
                <span className="meter-name">
                  <span className="meter-dot" style={{ background: f.color }} />
                  {f.name}
                </span>
                <span className="meter-used">{f.used} / {f.limit} tok</span>
              </div>
              <div className="meter-track">
                <div className="meter-fill" style={{ width: `${f.pct}%`, background: f.color }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="settings-row-2">
        <div className="settings-card">
          <div className="settings-card-title"><IconCoin />Cost this cycle</div>
          <div className="cost-total-row">
            <span className="cost-total-value">$18.42</span>
            <span className="cost-total-label">resets Oct 1</span>
          </div>
          {COST_ROWS.map((c) => (
            <div className="cost-row" key={c.name}>
              <span className="cost-row-name">
                <span className="meter-dot" style={{ background: c.color }} />
                {c.name}
              </span>
              <span className="cost-row-value">{c.value}</span>
            </div>
          ))}
        </div>

        <div className="settings-card">
          <div className="settings-card-title"><IconClock />Recent activity</div>
          <div className="log-head-row">
            <span>Time</span>
            <span>Feature</span>
            <span>Model</span>
            <span>Tokens</span>
            <span>Cost</span>
          </div>
          {ACTIVITY_LOG.map((row, i) => (
            <div className="log-row" key={i}>
              <span className="log-time" title={row.time}>{row.time}</span>
              <span className="log-feature" title={row.feature}>
                <span className="log-dot" style={{ background: row.color }} />
                <span>{row.feature}</span>
              </span>
              <span className="log-model" title={row.model}>{row.model}</span>
              <span className="log-tokens">{row.tokens}</span>
              <span className="log-cost">{row.cost}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
