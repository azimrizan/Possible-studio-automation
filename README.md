# Possible Studio — AI Marketing Employee (POC)

An autonomous, human-governed AI social media and Meta ads platform designed for multi-tenant SaaS.

---

## Phase 0 Foundations: Delivered & Operational

- **Monorepo Structure:** Clean separation of concern across `apps/`, `packages/`, and `mcp-servers/`.
- **Infrastructure (Local Non-AWS POC):**
  - PostgreSQL 16 with `pgvector` & Row-Level Security (`RLS`).
  - Redis 7 cache & queue.
  - MinIO S3-compatible local object storage.
  - AES-256-GCM local secrets vault.
- **Backend API (`apps/api`):** FastAPI + SQLAlchemy 2 + JWT Auth + Tenant/Workspace RBAC (`OWNER`, `EDITOR`, `APPROVER`, `VIEWER`).
- **Cryptographic Security Layer:**
  - Ed25519 asymmetric signature engine.
  - Deterministic SHA-256 action payload hashing.
  - Single-use, hash-bound approval tokens for high-risk tools (`PUBLISH`, `SPEND`).
- **First-Party MCP Suite:**
  - `packages/mcp-common`: Standard base MCP server with defense-in-depth security.
  - `apps/mcp-gateway`: Capability router, policy engine, and tool proxy.
  - `mcp-servers/mcp-hello`: Hello World MCP server exposing safe and protected tools.
- **Model Gateway (`packages/model-gateway`):**
  - Provider-agnostic LLM interface with Mock adapter and cost accounting.
- **Frontend (`apps/web`):**
  - Next.js 14 App Router, TypeScript, Tailwind CSS, shadcn/ui dark theme, and interactive diagnostics console.

---

## Quickstart

### 1. Setup Environment
```bash
# Clone and enter directory
cd possible-studio-automation

# Copy environment template
cp .env.example .env
```

### 2. Run Tests
```bash
# Run backend unit and E2E acceptance tests
.venv/bin/pytest tests/ -v
```

### 3. Run Backend API
```bash
.venv/bin/uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be live at `http://localhost:8000/docs`.

### 4. Run Frontend Web App
```bash
npm --prefix apps/web run dev
```
Dashboard will be live at `http://localhost:3000`.

### 5. Running with Docker Compose (Optional)
```bash
docker compose up -d
```
