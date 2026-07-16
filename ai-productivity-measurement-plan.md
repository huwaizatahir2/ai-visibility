# Measuring AI Impact on Developer Productivity

**Scope:** One team (~5–15 developers)
**AI tool in scope:** Claude Code
**Approach:** DIY — instrument with tools we already own (GitHub, Jira, New Relic) + lightweight surveys
**Owner:** _(you)_ — proposed as an OKR contribution for the next release
**Status:** Draft plan / v1
**Source framework:** [DX — AI Measurement Hub](https://getdx.com/blog/ai-measurement-hub/) (DX Core 4, DXI, Utilization/Impact/Cost model)

---

## 1. The problem we're solving

We're adopting Claude Code but have **no objective read on whether it's actually making us more productive** — or by how much. Anecdote ("it feels faster") isn't defensible in an OKR review. We need a small, repeatable measurement system that:

- Establishes a **baseline before** AI usage is fully embedded.
- Separates **three different questions**: *Are we using it? Is it helping? Is it worth the money?*
- Combines **system data** (objective, gameable) with **self-report** (subjective, honest about experience).
- Reports at the **team level only** — never as individual surveillance (kills trust, corrupts the data).

> **Reality check from the data:** real productivity gains land around **5–15%, not 50–100%**. Heavy users do ship ~4–5× more PRs/week than non-users, but that's partly *who* adopts, not pure causation. Average measured time saved is **~3h45m/dev/week**. Set expectations there or the OKR looks like a failure when it's actually a win.

---

## 2. The framework (3 dimensions)

DX's model. Every metric we track answers exactly one of these:

| Dimension | Question | Gameable alone? | Needs pairing with |
|---|---|---|---|
| **Utilization** | Are devs actually using Claude Code? | Yes (usage ≠ value) | Impact |
| **Impact** | Is it improving speed, quality, experience? | Yes (speed can hurt quality) | Quality + DXI |
| **Cost** | Does the time saved beat what we spend? | — | Both above |

**Golden rule:** never report a metric from one dimension without one from another. "PR throughput up 30%" is meaningless next to a rising change-failure rate.

---

## 3. Metric catalog (mapped to our stack)

Legend — **Source:** where the number comes from. **Method:** `system` = pulled automatically, `survey` = quarterly, `sampling` = point-of-work pulse.

### 3.1 Utilization — *are we using it?*

| Metric | What it measures | Source (our stack) | Method | Cadence |
|---|---|---|---|---|
| Weekly active users (WAU) | % of team running Claude Code in a week | Claude Code OTel / Console Analytics | system | Weekly |
| Daily active users (DAU) | % using it daily (depth of adoption) | Claude Code OTel | system | Weekly |
| % of PRs AI-assisted | PRs where Claude Code touched the code | GitHub + sampling tag | sampling | Per PR |
| % of committed code AI-generated | Lines Claude wrote that reached `develop` | Claude Code `lines_of_code` metric | system | Weekly |
| Accept/reject rate | Edits suggested vs accepted | Claude Code `code_edit_tool.decision` | system | Weekly |
| Sessions & active time | Engagement depth per dev | Claude Code `session.count`, `active_time` | system | Weekly |

**Benchmarks:** even mature orgs only hit **60–70% weekly** / **40–50% daily** active. Sub-40% weekly = adoption problem, not a tool problem — fix enablement before judging impact.

### 3.2 Impact — *is it helping?*

**Speed**

| Metric | What it measures | Source | Method | Cadence |
|---|---|---|---|---|
| PR throughput | Merged PRs per dev per week (complexity-adjusted if possible) | GitHub | system | Weekly |
| PR cycle time | Open → merge duration | GitHub | system | Weekly |
| Lead time for change | Commit → production (DORA) | GitHub + deploy logs | system | Per release |
| Perceived rate of delivery | Do devs *feel* they ship faster? | Survey (DX Core 4) | survey | Quarterly |

**Quality** — the counterweight to speed:

| Metric | What it measures | Source | Method | Cadence |
|---|---|---|---|---|
| PR revert rate | Reverted PRs ÷ total PRs | GitHub | system | Weekly |
| Change failure rate (CFR) | % deploys causing incident/rollback (DORA) | New Relic incidents + deploy markers | system | Per release |
| Code maintainability | Is AI code understandable/modifiable? | Survey (DX Core 4) | survey | Quarterly |
| SonarQube new-code quality gate | New bugs/smells/coverage on AI-touched code | SonarQube (already in CI) | system | Per PR |

> We already run SonarQube on every PR and New Relic in prod — **these quality signals are free**, just need to be charted over time. This is our guard against "AI made us fast and sloppy."

**Developer experience**

| Metric | What it measures | Source | Method | Cadence |
|---|---|---|---|---|
| Developer satisfaction w/ AI | How devs feel about Claude Code | Survey | quarterly | Quarterly |
| Change confidence | Confidence shipping changes (DX Core 4) | Survey | quarterly | Quarterly |
| % time on feature dev vs toil | Is AI freeing us from grunt work? | Survey / time allocation | sampling | Monthly |
| Time saved per dev/week | Self-reported hours saved | Survey | survey | Quarterly |

### 3.3 Cost — *is it worth it?*

| Metric | Formula | Source |
|---|---|---|
| AI spend (total + per dev) | Claude Code usage cost | Anthropic Console / `cost.usage` metric |
| Net time gain per dev | `time_saved_hrs − (spend ÷ loaded_hourly_cost)` | derived |
| ROI multiple | `value_of_time_saved ÷ tooling_cost` | derived |

---

## 4. DX Core 4 — the 5 headline numbers for the OKR

If leadership only looks at five things, these are it (DX's validated set, blends DORA + SPACE + DevEx):

1. **PR throughput** — speed (system)
2. **Perceived rate of delivery** — speed felt (survey)
3. **DXI / developer experience** — experience (survey, see §6)
4. **Code maintainability** — quality (survey)
5. **Change fail %** — quality (system, New Relic)

Track all five **before** and **after** Claude Code ramps. The *delta* is the OKR story.

---

## 5. Instrumenting Claude Code (the system-data half)

Claude Code emits **OpenTelemetry metrics** — this is how we get usage/cost without manual logging.

**Enable per-dev (or via shared shell profile / managed settings):**

```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp          # or prometheus
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://<our-collector>:4317
```

**Metrics it exports** (verify exact names against current Claude Code monitoring docs — they evolve):

- `claude_code.session.count` — sessions started
- `claude_code.active_time.total` — engaged time
- `claude_code.lines_of_code.count` — lines added/removed (AI-authored)
- `claude_code.commit.count`, `claude_code.pull_request.count`
- `claude_code.code_edit_tool.decision` — accept vs reject
- `claude_code.token.usage`, `claude_code.cost.usage` — tokens + USD

**Two collection options:**

- **DIY OTel:** point the exporter at an OTel collector → Prometheus/Grafana, *or* straight into **New Relic** (we already use it — it ingests OTLP natively). One Grafana/New Relic dashboard = our usage + cost panel.
- **Console Analytics:** if we're on a Claude **Team/Enterprise** plan, Anthropic Console has a built-in usage/spend analytics view — zero setup, good enough to start.

**Spend:** pull from the **Anthropic Console** (billing/usage) for the authoritative cost number; reconcile against `cost.usage`.

---

## 6. Surveys (the self-report half)

System data can't tell you if code is *maintainable* or if devs *feel* faster. A short quarterly survey + occasional pulse covers it. Keep it **<3 min** or response rate dies.

**Quarterly survey (DX Core 4 items, 1–5 agree scale):**

- "Claude Code helps me deliver work faster." *(perceived delivery)*
- "Code produced with AI is easy to understand and modify." *(maintainability)*
- "I'm confident the changes I ship won't break things." *(change confidence)*
- "I'm satisfied using Claude Code in my workflow." *(satisfaction)*
- "How many hours did Claude Code save you this week?" *(time saved — the ROI input)*
- "% of your time this week on feature work vs. toil/boilerplate?" *(toil reduction)*

**DXI (optional, higher fidelity):** DX's Developer Experience Index is a composite of **14 evidence-based drivers**; each **+1 point ≈ 13 min saved/dev/week (~10 hrs/yr)**. Full DXI is really a DX-platform feature, but we can run a lite version (rate the 14 drivers 1–5, average) to get a trendable single number.

**Experience sampling (pulse):** one-click question at the moment of work, e.g. a PR-template checkbox **"Was this PR AI-assisted? [ ]"** and a post-review "Was this easy to understand? 👍/👎". Cheapest, most honest signal — captures the **% AI-assisted PRs** number for §3.1.

**Survey tooling (DIY):** Google Forms / a Slack workflow / a simple `/pulse` bot. No new vendor.

---

## 7. ROI math (worked for a 10-dev team)

Plug our real numbers; example uses placeholders.

```
Inputs
  devs                 = 10
  time_saved/dev/week  = 3.0 hrs        (use OUR survey number, not the 3h45m benchmark)
  loaded_hourly_cost   = $40/hr         (replace with our real loaded rate)
  Claude Code spend    = $X/month       (from Anthropic Console)

Value of time saved (per month)
  = 3.0 hrs × 10 devs × 4.3 weeks × $40
  = $5,160 / month

Net time gain
  = value_of_time_saved − spend
  = $5,160 − spend

ROI multiple
  = value_of_time_saved ÷ spend
```

**Benchmark ROI ranges** (50+ enterprise rollouts): small teams **150–250% over 3 yrs, 12–18 mo payback**; top-20% implementations **500%+**. A single worked example showing payback in <X months is usually enough for the OKR.

> **Caveat:** time-saved is self-reported and optimistic. Pair it with the **same-engineer throughput trend** (§3.2) as an objective cross-check before claiming a dollar figure.

---

## 8. Rollout roadmap

Aligns to the DX "baseline → deploy → correlate" model, compressed for one team.

| Phase | Weeks | Do |
|---|---|---|
| **0 — Baseline** | 1–2 | Snapshot PR throughput, cycle time, revert rate, CFR **before** heavy AI use. Run first survey. Document current time-on-feature-work. |
| **1 — Instrument** | 2–3 | Turn on Claude Code OTel → New Relic/Grafana. Add PR-template "AI-assisted?" checkbox. Stand up the dashboard. |
| **2 — Adopt & track** | 4–8 | Weekly WAU/DAU + pulse. Enablement for low adopters. **Don't judge impact yet** — allow 3–6 mo for real AI workflows to form. |
| **3 — Correlate** | 9–12 | Overlay usage against throughput/quality. Segment heavy vs light users. First ROI calc. |
| **Ongoing** | — | Monthly 1-page leadership report; quarterly deep-dive (metrics + a couple of dev interviews). |

---

## 9. Proposed OKR

**Objective:** Establish objective, trusted visibility into Claude Code's impact on team productivity.

**Key Results (this release):**

- **KR1** — Baseline + dashboard live for all 5 DX Core 4 metrics by end of week 3.
- **KR2** — ≥70% weekly active Claude Code usage across the team, sustained 4 weeks.
- **KR3** — Quarterly DX survey shipped with ≥80% response rate; baseline DXI-lite score recorded.
- **KR4** — First ROI report published: net-time-gain/dev and payback period, with throughput cross-check.
- **KR5** — No regression in quality guardrails (revert rate, CFR, SonarQube new-code gate) vs. baseline.

KR5 is deliberately a *guardrail* — it stops us "winning" on speed while quietly degrading quality.

---

## 10. Guardrails & pitfalls (don't skip)

- **Team-level aggregation only.** Never rank individuals on AI usage or throughput — it turns the metric into a target and people game it (Goodhart's law).
- **Baseline first.** Once AI is fully embedded you can't reconstruct the "before." This is the one irreversible step — do it in week 1.
- **Pair every metric.** Speed without quality is a trap.
- **Give it 3–6 months.** Early numbers reflect a learning curve, not the steady state. Don't write the OKR verdict at week 4.
- **System data is gameable, surveys are biased — use both.** They cross-check each other.
- **Beware selection bias.** Heavy users shipping 4× more PRs may just be your already-strong devs. Use **same-engineer before/after** to isolate the AI effect.
- **Expect 5–15%, not 2×.** Anchor leadership there up front.

---

## 11. What this costs us to run

| Item | Cost |
|---|---|
| Claude Code OTel → New Relic | $0 (New Relic already in stack, OTLP native) |
| GitHub / Jira / SonarQube metrics | $0 (already own) |
| Surveys (Google Forms / Slack) | $0 |
| Setup effort | ~3–5 dev-days (dashboard + survey + PR template) |
| Ongoing | ~2 hrs/month (report) + survey time |

DIY path = **no new vendor spend**. If the baseline proves value, the upgrade pitch is a **DX platform** (getdx.com) for DX Core 4, real DXI, and TrueThroughput out-of-the-box — revisit at quarter end.

---

## Appendix A — Metric → source quick reference

| Metric | Tool | Pull via |
|---|---|---|
| Usage, tokens, cost, accept-rate | Claude Code | OTel export / Anthropic Console |
| PR throughput, cycle time, revert rate, % AI-assisted | GitHub | GitHub API / MCP |
| Lead time, deploy frequency | GitHub + deploy logs | CI/CD |
| Change failure rate, incidents | New Relic | New Relic MCP / NRQL |
| New-code bugs/smells/coverage | SonarQube | SonarQube MCP |
| Throughput / lead time (work items) | Jira | Atlassian MCP |
| Perceived delivery, maintainability, confidence, DXI, time-saved | Surveys | Google Forms / Slack |

## Appendix B — Sources

- DX, *AI Measurement Hub* — https://getdx.com/blog/ai-measurement-hub/
- DX Core 4 (DORA + SPACE + DevEx blend)
- Claude Code monitoring/telemetry docs (verify current OTel metric names)
- DORA metrics (lead time, deploy freq, CFR, MTTR)
