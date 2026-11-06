# HealCloud Frontend — SRE Operational Console

This directory hosts the web-based SRE console and incident war room for the HealCloud platform.

## 🛠️ Tech Stack
- **Framework:** Next.js 14+ (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS & Lucide Icons
- **State Management & Caching:** TanStack Query (React Query)
- **Real-Time Updates:** WebSockets (`/api/v1/ws/incidents`)

## 📁 Architecture Preview
```text
frontend/
├── app/                  # Next.js 14 App Router routes & layouts
│   ├── dashboard/        # Global reliability dashboard
│   ├── incidents/        # Incident War Room & diagnostic views
│   ├── playbooks/        # Playbook editor & visual builder
│   └── settings/         # Cloud credentials & integrations
├── components/           # Reusable UI component library
│   ├── ui/               # Base primitives (buttons, modals, badges)
│   ├── incidents/        # Incident timeline, RCA card, approval modal
│   └── topology/         # Service dependency graph canvas
├── hooks/                # WebSocket listeners & data fetching hooks
└── lib/                  # API client & formatting utilities
```

## 🚀 Quickstart
```bash
pnpm install
pnpm dev
```
Runs at `http://localhost:3000`.

