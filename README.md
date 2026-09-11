# SAFIRE — Sovereign On-Premise Agentic AI Workbench

> **Smart India Hackathon 2026**
> Sprint 0 — Foundation + Contract Freeze

---

## Overview

SAFIRE is a sovereign, on-premise agentic AI workbench designed for secure,
auditable AI operations. The system runs entirely within an organization's
infrastructure — no data leaves the premises.

**Architecture:** Modular monolith with an isolated execution-service boundary,
prepared for later sandbox execution.

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python · FastAPI |
| **Frontend** | Next.js · React · TypeScript |
| **Database** | PostgreSQL · pgvector |
| **Deployment** | On-premise · Docker (local-first) |

## Repository Structure

```
sih-2026/
├── backend/        # FastAPI application
├── frontend/       # Next.js application
├── shared/         # Shared schemas, types, and contracts
├── tests/          # Integration and end-to-end tests
├── docs/           # Documentation and ADRs
│   └── adr/        # Architecture Decision Records
├── .editorconfig   # Editor formatting rules
├── .env.example    # Environment variable template
└── .gitignore      # Git ignore rules
```

## Prerequisites

- Python 3.11+
- Node.js 20 LTS+
- npm 10+
- PostgreSQL 16+ with pgvector extension
- Git 2.40+

## Getting Started

```bash
# 1. Clone the repository
git clone https://github.com/hiya-05-50/sih-2026.git
cd sih-2026

# 2. Copy environment template
cp .env.example .env
# Edit .env with your local values

# 3. Backend setup (details in backend/README.md — coming in Phase 2)

# 4. Frontend setup (details in frontend/README.md — coming in Phase 2)
```

## Sprint Roadmap

| Sprint | Focus | Status |
|--------|-------|--------|
| **Sprint 0** | Foundation + Contract Freeze | 🔨 In Progress |
| Sprint 1+ | Feature implementation | ⏳ Planned |

## Team

This project is developed by Team **hiya-05-50** for SIH 2026.

## License

This is a private repository. All rights reserved.
