# UI/UX Specification & Design System

| **Document Title** | HealCloud SRE Operational Console UI/UX Design System |
| :--- | :--- |
| **Document Version** | 1.0.0 |
| **Status** | Approved |

---

## 1. Design Philosophy for High-Stress SRE Environments

During severe production outages, cognitive overload is the primary source of human error. The HealCloud SRE Console is engineered around three foundational tenets:

1. **Immediate Situational Awareness (Sub-Second Triage):** The exact failing service, blast radius, and proposed fix must be instantly visible above the fold.
2. **Progressive Disclosure:** High-level state is prioritized; deep telemetry, raw logs, and stack traces remain one click or keypress away.
3. **Fail-Safe Ergonomics:** Destructive actions require deliberate multi-step confirmation or keyboard-held key combos to prevent accidental clicks under pressure.

---

## 2. Design Tokens & Visual Hierarchy

### 2.1 Theme & Color Palette
- **Default Theme:** Dark Mode (Optimized for low-light NOC / multi-monitor control rooms).
- **Backgrounds:**
  - Base: `#0B0F19` (Deep Slate)
  - Card / Panel: `#111827` (Charcoal Gray)
  - Border: `#1F2937` (Muted Zinc)
- **Status & Risk Indicators:**
  - `P1 / CRITICAL / FAILED`: `#EF4444` (Vibrant Coral Red)
  - `P2 / WARNING / AWAITING`: `#F59E0B` (Amber Warning)
  - `HEALTHY / RESOLVED / AUTO-HEALED`: `#10B981` (Emerald Green)
  - `ACTIVE / RUNNING / DIAGNOSING`: `#3B82F6` (Electric Blue)
  - `INFO / NEUTRAL`: `#6B7280` (Cool Gray)

### 2.2 Typography
- **Primary Interface Font:** `Inter` or `Geist Sans` (High legibility at small sizes).
- **Telemetry, Code & Logs:** `JetBrains Mono` or `Fira Code` (Monospaced with tabular figures).

---

## 3. Information Architecture & Navigation

```text
┌────────────────────────────────────────────────────────────────────────┐
│  HealCloud   [Global Health: 99.8%]   [Active: 2 Incidents]  [Sarah (SRE)]
├────────────────────────────────────────────────────────────────────────┤
│  Navigation: [Dashboard]  [Incidents]  [Playbooks]  [Topology]  [Audit] 
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  [Main Content Area]                                                  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Key Screens & Wireframe Schematics

### 4.1 Global Operations Dashboard (`/dashboard`)
Displays real-time reliability pulse across all connected cloud regions and clusters.

```text
┌────────────────────────────────────────────────────────────────────────┐
│ METRIC SUMMARY CARDS                                                   │
│ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌───────────┐ │
│ │ Mean MTTR      │ │ Auto-Heal Rate │ │ Active P1/P2   │ │ Guardrails│ │
│ │ 2m 14s (-68%)  │ │ 94.2% (48/51)  │ │ 1 Pending HITL │ │ 0 Tripped │ │
│ └────────────────┘ └────────────────┘ └────────────────┘ └───────────┘ │
├────────────────────────────────────────────────────────────────────────┤
│ ACTIVE INCIDENTS FEED (Real-Time WebSocket Stream)                     │
│ [P1] INC-1049 | Memory leak in checkout-api | Confidence: 94% | [REVIEW]│
│ [P2] INC-1048 | Latency spike on auth-cache | Status: Auto-Healing 40% │
│ [P3] INC-1045 | Disk pressure on node-04    | Status: Resolved (2m ago)│
├────────────────────────────────────────────────────────────────────────┤
│ INFRASTRUCTURE HEALTH MATRIX (Kubernetes & Multi-Cloud Clusters)       │
│  [us-east-1-prod: 🟢 Healthy]  [eu-central-1-prod: 🟡 Degraded (1 pod)]│
└────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Incident War Room & Diagnostic Tree (`/incidents/[id]`)
Unified view for single-incident deep-dive and remediation authorization.

```text
┌────────────────────────────────────────────────────────────────────────┐
│ INC-1049: Memory Saturation & OOMKill risk in checkout-api              │
│ Status: [AWAITING APPROVAL]  Severity: [P1 CRITICAL]  Triggered: 12:31Z │
├───────────────────────────────────┬────────────────────────────────────┤
│ ROOT CAUSE ANALYSIS (RCA)         │ RECOMMENDED REMEDIATION PLAYBOOK   │
│ Confidence: 94%                   │ Playbook: Canary Rollback (v2.13.9)│
│                                   │ Risk Tier: TIER 3 (High Risk)      │
│ Summary:                          │ Blast Radius: 1 Deployment (3 Pods)│
│ Heap memory leak detected after   │                                    │
│ deployment revision v2.14.0.      │ Proposed Actions:                  │
│                                   │ 1. Roll back deployment to v2.13.9 │
│ Evidence Correlated:              │ 2. Verify health probe over 60s    │
│ • container_memory_working_set >92% 3. Auto-rollback if unhealed       │
│ • 18 OutOfMemoryError log lines   │                                    │
│ • Trace latency spike +340ms      │ [ REJECT ]   [ APPROVE & EXECUTE ] │
├───────────────────────────────────┴────────────────────────────────────┤
│ LIVE TELEMETRY & EVENT STREAM                                          │
│ 12:30:15Z - Prometheus alert received: ContainerMemoryHighAllocation   │
│ 12:30:22Z - RCA Engine correlated deployment event sha-8f921bc         │
│ 12:30:45Z - Guardrail check: Cooldown OK, Requires Human Approval Gate │
└────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Human-in-the-Loop (HITL) Approval Modal
When an operator clicks **"APPROVE & EXECUTE"**, a high-visibility modal opens:

```text
┌───────────────────────────────────────────────────────────────┐
│ ⚠️ AUTHORIZE TIER 3 REMEDIATION ACTION                        │
├───────────────────────────────────────────────────────────────┤
│ Target Service : production / checkout-api                    │
│ Action         : Rollback deployment to v2.13.9               │
│ Guardrail Check: PASSED (Under cluster concurrency limit)     │
│ Safety Net     : Auto-rollback enabled if health fails in 60s │
│                                                               │
│ Operator Note (Optional):                                     │
│ [ Verified heap memory graphs. Proceeding with rollback... ]  │
│                                                               │
│ Hold [Shift + Enter] or click below to authorize:             │
│                                                               │
│      [ Cancel ]          [ 🚀 Confirm & Execute Action ]      │
└───────────────────────────────────────────────────────────────┘
```

---

## 5. Keyboard Navigation & Operator Shortcuts

In high-pressure situations, full keyboard navigation enables sub-second incident review without touching a mouse:

| Shortcut | Action |
| :--- | :--- |
| `j` / `k` | Move cursor down / up across the incident list |
| `Enter` or `o` | Open selected incident war room |
| `a` | Trigger "Approve Remediation" modal |
| `x` or `Esc` | Dismiss modal / Reject proposed action |
| `/` | Global search across services, logs, and incidents |
| `r` | Force refresh telemetry snapshot |
| `?` | Toggle keyboard shortcuts cheat-sheet |

---

## 6. Accessibility & Performance Standards

- **Color Contrast:** Conforms to **WCAG 2.1 AA** (minimum 4.5:1 contrast ratio for text and status tokens).
- **Latency Budget:** First Contentful Paint (FCP) $< 0.8\text{s}$, Time to Interactive (TTI) $< 1.5\text{s}$.
- **WebSocket Reconnection:** Automatic exponential backoff reconnection with an offline status banner if network connectivity drops.

