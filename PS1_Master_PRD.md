# SAFIRE_MASTER_PRD_v1.1

**Document Status:** Master PRD v1.1 (hardened/reconciled)
**Source:** Official SIH PS 26117 + SAFIRE competitive research + PRD v1.0 + Technical Architecture & Implementation Specification v0.1 + PRD-vs-Technical-Architecture Review + Team Research & Strategy Dossier + Architecture Diagram
**Current Date:** 7 September 2026
**Internal Hackathon:** 12 September 2026 (5 days remaining)
**Status:** Implementation-ready after the Day-1 (7 Sep) bake-off decisions in §37/§43 are closed.

This document supersedes PRD v1.0 as the product-level source of truth. It does not redesign the SAFIRE architecture — it reconciles known contradictions (identified in the PRD-vs-Technical-Architecture Review), closes missing contracts, tightens MVP scope for the compressed timeline, and makes every mandatory SIH requirement demonstrable. The Technical Architecture & Implementation Specification remains the implementation authority for anything this document does not itself decide, subject to the bake-off outcomes in §37.

**Evidence labels used throughout:** `CONFIRMED` (official PS or an authoritative cited source) · `OBSERVED` (seen in a public product/repo, not claimed as SAFIRE-equivalent) · `PROPOSED` (a SAFIRE design decision) · `PENDING` (proposed but not yet finalized) · `DECIDED` (the team has committed) · `TO BE VALIDATED` (requires measurement before being stated as fact). No benchmark numbers in this document are results — all are targets pending SIAB measurement.

---

## 1. Executive Summary

SAFIRE is a sovereign, model-agnostic AI execution fabric — not a chatbot — for confidential industrial knowledge work at organizations like MRPL that cannot let this class of data reach cloud AI services. `PROPOSED` It routes each task to the smallest local model capable of doing it well, grounds every important claim in evidence traceable to the organization's own documents, checks its own numeric and rule-based conclusions deterministically before a human ever relies on them, escalates to a stronger model or a human only when it actually needs to, and turns the result into a real, provenance-linked deliverable — while continuously proving, via a live monitor, that nothing has left the network.

This v1.1 hardening pass makes fourteen specific corrections relative to earlier drafts (§10 onward), the most consequential being: **R8 (spreadsheet work) is now unambiguously P0** and integrated into the flagship demo; **VRAM/model-residency assumptions are now conditional on measurement**, with sequential swapping as the guaranteed fallback; **the capability vocabulary is now a single canonical taxonomy** split into model capabilities and pipeline capabilities; and **the remaining timeline is now five real days (7–12 September)**, not the original nine, with P0 scope tightened accordingly.

Positioning is unchanged and non-negotiable: **the model is replaceable; the execution fabric is the product.** LLMs propose; evidence, deterministic verification, policy, and humans provide control.

---

## 2. Official Problem Statement

`CONFIRMED`, PS 26117 (Mangalore Refinery and Petrochemicals Limited, Theme: Smart Automation). Refineries, PSUs, and defence-linked manufacturing generate large volumes of sensitive knowledge work — approval notes, board presentations, engineering calculations, internal tool code, review of scanned drawings and inspection reports — that cannot go through cloud AI assistants because the underlying data (P&IDs, financials, vendor negotiations, unreleased designs, correspondence, business strategy) is confidential. Policy keeps this data on-premises, so staff either work manually or paste confidential material into public tools anyway. Open-weight models are now capable enough that a genuinely useful, deployable assistant is realistic, but nothing suitable exists yet.

**Expected solution** (`CONFIRMED`): a self-hosted, air-gapped workbench on the org's own GPU server; not locked to one model; automatic per-task model selection shown across at least two task types; extensible to new models without redesign; genuinely agentic (multi-step, tool-using, iterative); multimodal (scanned PDFs, handwriting, drawings, photographs) via local OCR/vision; real deliverables (DOCX/PPT/XLSX/code/calculations); grounded in the org's own manuals/SOPs/correspondence via a local knowledge base; and demonstrable, visible proof — logs or a network monitor — of zero external calls throughout. `CONFIRMED` open-source sample documents/P&IDs are explicitly sufficient for the demo; no proprietary MRPL data is required.

| Requirement | Meaning | Why it matters | SAFIRE response |
|---|---|---|---|
| R1 On-premise/air-gapped | Runs entirely on org infrastructure | The entire reason cloud AI is off-limits | Infrastructure Layer + default-deny network |
| R2 Multiple open-weight models | Not locked to one model | Different tasks need different model strengths | Model Plane registry |
| R3 Automatic model selection | System picks the model, not the user | Usability + efficiency | Control Plane router (§14) |
| R4 Extensible without redesign | New models addable | Field moves fast | Registry + adapter interface |
| R5 Genuine agentic behavior | Multi-step, tool-using, iterative | PS explicitly distinguishes this from one-shot chat | Agent runtime (§18) |
| R6 Local file read/write | Real file actions | A workbench, not just chat | Tool Plane (§19) |
| R7 Sandboxed code execution | Safe code running | PS explicitly requires this, verified | Coding sandbox (§20) |
| R8 Spreadsheet work | Explicitly named capability | Refinery data is naturally tabular | XLSX in flagship demo — **now P0** (§10, §31) |
| R9 Internal document search | Grounds answers in org knowledge | Prevents ungrounded generation | Knowledge/RAG Plane (§17) |
| R10 Multimodal understanding | Scanned docs, handwriting, drawings, photos | Real industrial documents aren't clean text | Document Intelligence (§16) |
| R11 Local OCR/vision | No cloud vision calls | Same confidentiality constraint applies to images | On-device OCR/VLM pipeline |
| R12 Real deliverables | DOCX/XLSX/PPTX/code, not chat | Business value is the artifact | Artifact Engine (§26) |
| R13 Visible zero-egress proof | Logs/monitor, not a claim | "Proof of the sovereign claim, not just a statement of it" (PS, verbatim intent) | Sovereignty Plane, live dashboard (§25) |

---

## 3. Problem Context

`CONFIRMED` the PS states directly that the current alternative to a proper sovereign tool is either lost productivity (manual work) or a live data-exfiltration risk (staff pasting confidential material into public AI tools). `INFERENCE` this framing means SAFIRE's success criterion isn't "is the AI capable" — most modern open-weight models clear a reasonable capability bar — it's "is the AI trustworthy enough, and demonstrably safe enough, that a real approval note can depend on it." That reframing drives nearly every architectural choice in this document (evidence objects, verification fabric, risk tiers, sovereignty proof).

---

## 4. Users / Personas

| Persona | Job-to-be-done | Risk tier they operate in |
|---|---|---|
| Inspection Engineer | Turn a scanned report into an evidence-backed approval note quickly | AMBER |
| Maintenance Planner | Reconcile current readings against SOP thresholds and history | AMBER |
| Plant Engineer/Coder | Generate and verify small internal scripts/calculations | GREEN/AMBER |
| Shift Supervisor/Approver | See evidence and reasoning before signing off | Approval gate (RED/AMBER) |
| IT/Security Administrator | Prove, continuously, that nothing left the network | Governance |

`PROPOSED` explicitly out of scope: SCADA operators, ERP-integrated roles, any role requiring direct physical-equipment control (§6).

---

## 5. Goals

`PROPOSED` demonstrate, on a single mid-range-GPU workstation: air-gapped multi-model agentic execution; one full document→verified-decision-package workflow including a spreadsheet output; a sandboxed, self-correcting coding task; a multimodal understanding task; live, visible proof of zero egress; resistance to a prompt-injection attempt; correct handling of conflicting evidence.

---

## 6. Non-Goals

`PROPOSED`, explicit: no direct SCADA/DCS or physical-equipment control; no ERP/CMMS integration; no multi-GPU/distributed inference; no production-grade RBAC/SSO; no full GraphRAG (only an optional lightweight graph where relationships genuinely matter); SAFIRE never replaces engineering judgment on RED-risk decisions — it supports, it never autonomously decides.

---

## 7. Product Vision

> A sovereign, model-agnostic AI execution platform for confidential industrial knowledge work.

Lifecycle: `UNDERSTAND → RETRIEVE → REASON → ACT → VERIFY → APPROVE → DELIVER → AUDIT`

---

## 8. Core Principles

`PROPOSED`, binding on every design decision in this document:

1. **The model is replaceable; the execution fabric is the product.**
2. **LLMs propose; evidence, deterministic verification, policy, and humans provide control.**
3. Sovereignty first — no mandatory cloud dependency anywhere in the core path.
4. Model agnosticism via registry + adapter, never hard-wired calls.
5. Capability-aware routing, not "always the biggest model."
6. Best-sufficient-model escalation: SMALL → MEDIUM → LARGE → HUMAN.
7. Evidence-first reasoning — claims trace to Evidence Objects.
8. LLMs are not final authorities — deterministic checks sit beside every judgment.
9. Risk-adaptive autonomy — GREEN automatic, AMBER validated, RED validated + human.
10. Documents are untrusted data, never instructions.
11. Least-privilege tool access, always.
12. Sovereignty is enforced and demonstrated — never merely asserted, and never claimed as absolute ("100% secure" is not a phrase this project uses — see §25).
13. Artifact-first value — the deliverable is the product, not the chat transcript.
14. Everything measurable feeds SIAB (§29); nothing is claimed before it's measured.

---

## 9. Competitive Landscape (Summary)

`CONFIRMED`/`OBSERVED` full detail lives in the Team Research & Strategy Dossier (§4–§6 there); summarized here for product context. A public repository already targets this exact PS (github.com/Varadraj2327/sovereign-ai-workbench). Mature local-AI platforms (Open WebUI, AnythingLLM) already combine local models, RAG, and agent tooling; agent-workflow platforms (Dify, LangGraph) and coding agents (OpenHands, Open Interpreter) already demonstrate multi-step tool use and sandboxed execution; industrial AI platforms (Cognite, Siemens) and sovereign-infrastructure vendors (NVIDIA, Dell, HPE, Sarvam) address adjacent but different layers of the problem.

**What is explicitly not a standalone differentiator** (`PROPOSED`, do-not-claim list): local LLM inference, open-weight models, RAG, multimodal/OCR, agents/tool calling, code execution, RBAC, audit logging, human approval, or model selection — each already exists, individually or combined, somewhere in the reviewed landscape.

---

## 10. Differentiation

`PROPOSED` the strategic gap: a system-level execution fabric combining capability-aware model routing, resource-aware escalation, evidence-native reasoning, verification-first execution, deterministic validation alongside LLM judgment, risk-adaptive autonomy, policy-governed tools, provenance-aware artifacts, visibly demonstrated sovereignty, and integrated benchmarking (SIAB). No single item in this list is claimed as unique; the combination, applied structurally rather than as add-on features, is what our research did not find publicly documented elsewhere.

---

## 11. Product Architecture

The nine-plane architecture is unchanged from the submitted diagram and is preserved as-is in this hardening pass:

1. **Experience Plane** — enterprise workbench UI
2. **Intelligent Control Plane** — task understanding → capability planning → model routing → resource optimization → context management → agent runtime → escalation
3. **Model Plane** — local model registry (vision, reasoning, coding, embedding, reranker)
4. **Knowledge & Data Plane** — document intelligence, hybrid retrieval, evidence store, optional graph
5. **Tool & Action Plane** — file ops, search, spreadsheet ops, calculation, sandboxed Python, document generation, image/diagram tools, validation
6. **Verification & Policy Fabric** — evidence/retrieval/calculation/rule/schema/artifact/permission checks → PASS/FAIL/ESCALATE/APPROVE
7. **Sovereignty & Observability Plane** — zero-egress enforcement, network monitor, audit logs, execution tracing, performance metrics, SIAB runner
8. **On-Premise Infrastructure Layer** — GPU workstation, local inference runtime, containers, storage, database, air-gapped network
9. **Deliverables & Business Value** — approval notes, spreadsheets, presentations, code, calculations, reports

**Explicit plane boundary clarification (§20 of the hardening instructions, now resolved):** Plane 7 (Sovereignty & Observability) owns *runtime* network enforcement and monitoring — is the process tree making external calls, right now. Cross-cutting governance owns *authorization* — who/what is permitted to do what (RBAC, tool permissions, data classification). Plane 8 (Infrastructure) owns *where* the software physically runs (hardware, containers, storage). These three are related but distinct, and no component should conflate them: a tool being *permitted* to run (governance) is a different question from it being *unable to reach the network* (Plane 7) and from *which machine* it runs on (Plane 8).

---

## 12. Functional Requirements

Covered in full via the Traceability Matrix (§40). Summary by plane: task intake and understanding (Control Plane); model registration, capability declaration, and routing (Model Plane, Control Plane); document ingestion, OCR/vision, evidence extraction (Knowledge & Data Plane); hybrid retrieval (Knowledge & Data Plane); agentic multi-step execution with typed tools (Tool & Action Plane, Agent Runtime); sandboxed code execution (Tool & Action Plane); spreadsheet, document, and calculation tools (Tool & Action Plane); deterministic verification of evidence, retrieval, calculation, rule, schema, artifact, and permission (Verification & Policy Fabric); risk classification and human approval (Verification & Policy Fabric); artifact generation with provenance (Deliverables); audit logging and live sovereignty monitoring (Sovereignty & Observability Plane).

---

## 13. Non-Functional Requirements

`PROPOSED`: air-gapped operation with no mandatory internet dependency for the core path; operation on a single mid-range-GPU workstation (RTX 4060, 8 GB VRAM — `CONFIRMED` hardware baseline); model swap/load latency visibly communicated to the user rather than hidden; deterministic, explainable model routing (no opaque learned policy in the MVP — §14); immutable, tamper-evident audit logging; least-privilege tool execution; artifact structural and semantic validity (§27) before delivery; live network observability during any demo run. Exact latency/throughput targets are `TO BE VALIDATED` via SIAB (§29) — not asserted here as fixed SLAs.

---

## 14. Intelligent Control / Routing

**Correction #4 applied.** The MVP router is **deterministic and explainable** — no learned routing policy is built or tuned during the MVP, because there isn't enough benchmark history in five days for such a signal to be meaningful.

```
Task → Task Profile → capability filter → feasibility filter →
candidate scoring → selected model → fallback/escalation
```

- **Capability filter:** hard-eliminates any model missing a required `model_capability` (§8 taxonomy below).
- **Feasibility filter:** hard-eliminates any model that doesn't fit current measured VRAM/resource availability.
- **Candidate scoring** (`PROPOSED`, deterministic weighted sum, all weights and inputs inspectable): task-capability fit, resource fit, latency fit, measured benchmark quality (once SIAB has run — `null`/neutral until then), and task risk/criticality. **Historical success is explicitly an extension point, treated as neutral/inactive during the MVP** — it is not built or tuned before enough benchmark runs exist, per Correction #4.
- **Selected model + fallback/escalation:** if no candidate scores above a minimum bar, or verification fails downstream, the Escalation Manager promotes to the next-strongest available model or to a human — never silently.

**Routing rationale is recorded in the execution trace, human-readable, e.g.:**
```
Selected model: Local Vision Model
Reason: Requires VISION + OCR + TOOL_CALLING.
Fits current VRAM/resource constraints.
Highest measured quality among feasible candidates.
```
This is a product requirement, not an implementation detail — the routing decision must be legible to a judge or an approver, not just logged internally.

---

## 15. Model Strategy

Registry-based, not hard-wired: every model declares capabilities (§ below), context length, VRAM footprint, quantization, tool-calling support, license, and a benchmark profile (initially `null`, populated once SIAB runs). Application logic talks only to a standard adapter interface (`generate`, `stream`, `tool_call`, `health_check`, `capabilities`), so adding a model is a registry entry, not a code change — this is the structural answer to R4.

**Correction #7 applied — VRAM/model residency:** `DECIDED` — sequential model swapping is the guaranteed MVP fallback. Concurrent residency of two or more models is treated strictly as an optimization, and is only claimed as available **after** it is measured on the actual demo hardware (§37 bake-off item). Illustrative VRAM figures used in earlier drafts (e.g., "8 GB for one quantized vision model" on an 8 GB card) are explicitly **not** treated as validated — they were an oversight in earlier drafts, corrected here. The team must measure: actual usable VRAM (after OS/driver overhead), model loading time, cold-start latency, warm-inference latency, model-switch latency, and whether any two required models can coexist in the measured budget. If they cannot, the demo UI must show a visible "switching model…" state — the product must never imply an instantaneous handoff it hasn't earned.

**Correction #3 applied — canonical capability taxonomy.** Exactly two categories, never mixed:

**A. Model capabilities** (things a model itself provides): `TEXT, VISION, OCR, DOCUMENT_UNDERSTANDING, REASONING, CODING, TOOL_CALLING, STRUCTURED_OUTPUT, LONG_CONTEXT, EMBEDDING, RERANKING`

**B. Pipeline capabilities** (things the SAFIRE system provides, not the model): `RETRIEVAL, EVIDENCE_EXTRACTION, CALCULATION, VALIDATION, DOCUMENT_GENERATION, SPREADSHEET_GENERATION, ARTIFACT_GENERATION`

The Task Profile must carry both, separately:

```json
{
  "required_model_capabilities": ["VISION", "OCR", "REASONING", "TOOL_CALLING"],
  "required_pipeline_capabilities": ["RETRIEVAL", "VALIDATION", "DOCUMENT_GENERATION", "SPREADSHEET_GENERATION"]
}
```

This single vocabulary replaces all earlier inconsistent examples (lowercase/uppercase mixes, `retrieval`/`document_generation`/`validation` incorrectly appearing as model capabilities) found in the Technical Architecture Specification draft and flagged by the Review. Every subsystem (Model Registry, Task Profile, Capability Planner, Router) must use this exact vocabulary — no local variants.

**Candidate model families to evaluate** (not locked, `TO BE VALIDATED` in §37): Qwen, GPT-OSS, Llama, Mistral-class open-weight models, across vision/multimodal, reasoning, coding, and embedding roles.

---

## 16. Document Intelligence

Pipeline: `DOCUMENT → type detection → text/OCR → layout → tables → images → handwriting → structured representation → Evidence Objects → indexing`. Candidate tools: Docling (`CONFIRMED`, structured document parsing) and PaddleOCR PP-StructureV3 (`CONFIRMED`, layout/OCR/table pipeline) — selected via the Day-1 document bake-off (§37) on the team's actual sample documents, not on paper specs.

**Correction #12 applied — multimodal context budgeting.** The pipeline must not blindly send an entire large scanned document into one enormous VLM call. `DECIDED` approach: `document parsing → identify difficult/relevant pages (e.g., pages with tables, low-confidence OCR, or images) → targeted VLM processing on those pages only → evidence creation`. The bake-off must explicitly measure max reliable pages/images per inference call, not just per-page OCR accuracy, and visual-token cost must be accounted for in context-budget planning. Multimodal output caching/reuse across repeated queries on the same document is treated as a later optimization, not an MVP requirement.

---

## 17. Knowledge / RAG

Hybrid retrieval: lexical/BM25 + dense vector search + metadata filtering + reranking, over fields like equipment ID, document type, revision, department, date, access level. `DECIDED` (MVP): PostgreSQL + pgvector, for operational simplicity on a single workstation. OpenSearch or a dedicated vector DB are `DEFERRED` — not introduced merely because they sound more enterprise-grade (per hardening instruction §31). Optional lightweight knowledge graph (`PROPOSED`, P2, not mandatory): used only where relationships genuinely matter (equipment → system → finding → SOP → work order), preferring an in-Postgres adjacency model over a full GraphRAG pipeline for MVP purposes.

**Explicit distinction (per §15 taxonomy):** retrieval, reranking, and evidence extraction are *pipeline capabilities* the Knowledge & Data Plane provides — never something a model "has."

---

## 18. Agent Runtime

State machine: `INTAKE → CLASSIFY → PLAN → RETRIEVE/TOOL → OBSERVE → VERIFY → (PASS→next / FAIL→REPLAN / ESCALATE→stronger model or human / APPROVE→DELIVER) → AUDIT`. State, memory/context, retries, tool-output validation, and resumability after failure are explicit, not implicit.

**Correction (Agent runtime decision, §32 of hardening instructions):** LangGraph (`CONFIRMED` open-source agent state-machine framework) vs. a small custom state machine remains a Day-1 bake-off decision (§37), evaluated on implementation speed, debuggability, and demo reliability under time pressure — not chosen "for appearance." Whichever wins, the orchestration layer remains plumbing; the differentiator is what happens at VERIFY and APPROVE, not which framework runs the loop.

---

## 19. Tool Plane

`DECIDED` P0 typed tool set: `read_document, search_knowledge, extract_table, inspect_image, calculate, run_python, create_docx, create_xlsx, validate_artifact, structured_file_read, structured_file_write`. **`create_xlsx` is now explicitly P0** (Correction #1 — see §31). P1: `create_pptx, create_pdf, compare_documents`. Every tool declares purpose, input/output schema, permissions, risk level, network requirement, resource limits, failure behavior, and audit behavior. No tool exposes unrestricted shell access.

---

## 20. Sandbox

Isolation: no network by default, CPU/RAM/time limits, restricted filesystem/subprocess access, controlled package access, captured output, guaranteed cleanup. Candidate mechanism: rootless Docker — validated against the actual demo OS (§37).

**Correction #11 applied — sandbox timeout.** "30 seconds" is not a universal rule; it is one configuration value that must be validated against the *actual chosen coding-demo task* before being finalized. Required configuration surface: default timeout, maximum timeout, CPU limit, RAM limit, network policy (none by default), filesystem policy (restricted to task workspace), subprocess policy (no arbitrary subprocess spawning).

---

## 21. Evidence / Provenance

**Correction #8 applied — Evidence Object contract, standardized.**

```json
{
  "evidence_id": "string",
  "document_id": "string",
  "page": 7,
  "section": "string",
  "region": { "x": 0.12, "y": 0.34, "width": 0.61, "height": 0.08 },
  "content": "string",
  "evidence_type": "string",
  "confidence": 0.0,
  "source_hash": "string",
  "extraction_method": "string",
  "timestamp": "ISO-8601",
  "access_level": "string"
}
```

`DECIDED`: `region` coordinates are normalized to 0–1 relative to the page (page-relative, not document- or pixel-absolute), resolving the previously undefined format flagged by the Review. Every downstream claim the agent makes must be attachable to one or more Evidence Objects; claims without one are flagged by the Verification Fabric (§22), not silently delivered.

---

## 22. Verification Fabric

The strongest single differentiator (§10) — a major subsystem, not a feature flag.

| Check | Question |
|---|---|
| Evidence verification | Is this claim supported by an Evidence Object? |
| Retrieval verification | Are the retrieved sources actually relevant? |
| Calculation verification | Can the numeric result be independently reproduced? |
| Rule verification | Does the result violate a known threshold/policy? |
| Schema verification | Does structured output conform to its schema? |
| Artifact verification | Is the generated file structurally *and* semantically valid (§27)? |
| Permission verification | Is the requesting actor allowed to perform this action? |
| Human verification | Does this task's risk tier require approval? |

Outcome states: **PASS → proceed, FAIL → replan/fix, ESCALATE → stronger model/human, APPROVE → deliver.**

**Correction #10 applied — calculation tolerance.** No universal hardcoded numeric tolerance (the earlier "0.01" example value is not a rule). Tolerance is a property of the calculation/rule definition itself:

```
expected_result → deterministic_recomputation → compare under RULE-SPECIFIC tolerance
  → PASS / FAIL / REPLAN
```

Each rule definition carries: expected numeric result (or formula), verification implementation reference, allowed tolerance (rule-specific), unit handling, and failure behavior.

---

## 23. Risk-Adaptive Autonomy

| Level | Examples | Autonomy |
|---|---|---|
| GREEN — informational | Summarization, retrieval, explanation | Automatic |
| AMBER — decision support | Calculation, inspection analysis, approval-note drafting | Deterministic validation required |
| RED — consequential | Approving actions, modifying operational data, privileged operations | Validation **and** mandatory human approval |

No RED-classified tool has operational-system write access in the MVP. `PROPOSED`, restated as a firm non-goal: SAFIRE does not attempt autonomous physical plant control.

---

## 24. Security / Policy

**Correction #7 applied — minimal identity model.** Full enterprise RBAC/SSO is not MVP scope, but policy, approval, and audit require a meaningful actor identity. `DECIDED` three local/demo roles:

| Role | Permissions |
|---|---|
| **ENGINEER** | Read/search, run calculations, sandbox execution, draft artifacts. **Cannot approve RED actions.** |
| **APPROVER** | Review; approve AMBER/RED actions where configured. |
| **ADMIN** | Manage models, tools, and policies. |

These are local/demo identities, not enterprise SSO — sufficient to make policy decisions, approvals, and audit events meaningful, and to make the unauthorized-tool-call acceptance test (§35) a real test rather than a trivially-true one.

Prompt-injection defense: documents are represented with an explicit trust boundary (`source=document, trust=untrusted`) before reaching reasoning; document content is never concatenated into a trusted system-instruction block. `CONFIRMED` this follows OWASP's GenAI top-listed risk category (prompt injection).

---

## 25. Sovereignty

**Correction #5 applied.** Four distinguished properties: **locality** (where inference/processing run), **isolation** (network/process controls, sandbox with no network by default), **enforcement** (a mechanism that makes an external call *fail*), and **observability** (a live monitor recording DNS/HTTP/TLS/outbound attempts in real time).

`PENDING`, explicitly not assumed: the actual demo OS, container runtime, network-isolation method, host egress enforcement, and monitoring method are **not yet determined** and must be resolved on 7 September (§37). Candidate mechanisms: Docker network isolation, Windows Firewall/WFP, Linux nftables/iptables, WSL2 isolation considerations, host firewall, local-only API binding. **Docker sandbox network isolation alone does not prove whole-system sovereignty** — the enforcement and monitoring must cover the actual application process tree, not just the coding sandbox.

The demo must show, live: external connections = 0, external DNS = 0, cloud/API calls = 0, and any blocked attempt explicitly logged.

**Language requirement (`DECIDED`):** this document and all team-facing materials use the phrase **"sovereignty is enforced and demonstrated"** — never "100% secure" or any equivalent absolute cybersecurity claim.

---

## 26. Artifact Engine

Business value is the deliverable, not the transcript. Coverage: DOCX, XLSX (now P0 — §10, §31), PPTX (P1), PDF (P1), code/scripts, calculations with shown steps. Rendering flow: `Agent structured result → Artifact schema → deterministic template renderer → validator → artifact`. The LLM produces a structured result (e.g., a `DecisionPackage` object); a deterministic renderer — not free-form LLM formatting — turns that into the actual file.

**Correction #9 applied — artifact validity, both dimensions required:**

| Dimension | Definition |
|---|---|
| **Structural validity** | The file is a valid, uncorrupted DOCX/XLSX/PDF that opens correctly in standard software |
| **Semantic validity** | Mandatory fields are present (per the `DecisionPackage`/`Inspection_Data` schema), expected content structure is present, evidence references are present, provenance is present where required |

For the flagship Decision Package, required fields are: executive summary, equipment identification, findings, evidence citations, calculations (with steps), matched SOP/manual clause, recommendation, risk/priority, approval status, and full provenance links. `validate_artifact` (§19) checks both dimensions before an artifact is considered complete.

---

## 27. UI/UX

`PROPOSED` core screens: Workbench (task intake), Task Execution View (live agent trace, including the human-readable routing rationale from §14), Evidence Explorer, Knowledge Base, Artifact Viewer, Model Registry & Status, Sovereignty Dashboard (live network monitor), Audit Trail, Benchmark Dashboard.

**Correction #13 applied — approval UI.** `DECIDED`: approval is **embedded within `/tasks/:id`**, not a separate standalone `/approvals` route, for MVP. Rationale: a dedicated approvals surface adds a screen the compressed five-day timeline doesn't need — the approval action is always in the context of a specific task, and embedding it keeps the approver's evidence and the approval control on the same view. This decision is explicit and final for MVP, not an oversight (as it was flagged in the Review).

---

## 28. API / Data

**Correction #14 applied — single API inventory**, no conflicting lists between sections:

`GET /health`, `GET /ready`, task endpoints (create/get/list tasks), document endpoints (upload/list/get), knowledge endpoints (search), evidence endpoints (get by ID), artifact endpoints (get/download), model endpoints (list/status), approval endpoints (approve/reject, scoped to a task), audit endpoints (list events), benchmark endpoints (run/get results). This is the canonical list; the Technical Architecture Specification's endpoint documentation must be reconciled against it, not maintained separately.

---

## 29. Benchmark / SIAB

**Correction #6 applied — reduced P0 scope.** SIAB (Sovereign Industrial AI Benchmark) exists to answer one question honestly: **are we better, and why?** `DECIDED` P0 contains exactly three configurations:

1. **Single strong local model** — no scaffolding.
2. **Generic agent + tools** — no verification fabric.
3. **Full SAFIRE.**

`DEFERRED` to P1/P2: additional baselines (single-model+RAG, an existing-workbench comparison) and architectural ablations (SAFIRE without router, without verification, vector-only, without escalation) — valuable, but building and validating nine configurations would jeopardize flagship-demo rehearsal time in a five-day window.

Measured dimensions: **Quality** (extraction F1, answer correctness, evidence correctness, citation correctness), **Reliability** (task completion, validation pass rate, recovery success), **Efficiency** (median/p95 latency, GPU/VRAM, CPU/RAM, model load time, model switch time, expensive-model call count, retries), **Security** (unauthorized-tool blocks, prompt-injection blocks, external-egress incidents — target: zero), **Human efficiency** (intervention rate, time-to-completion).

Reporting format (`DECIDED`, mandatory table shape — no invented values):

| Metric | Baseline | SAFIRE | Improvement | Confidence/sample size |
|---|---|---|---|---|
| (each metric above) | TO BE VALIDATED | TO BE VALIDATED | TO BE VALIDATED | TO BE VALIDATED |

---

## 30. Performance / Success Metrics

`TO BE VALIDATED` in all cases — no fixed SLA numbers are asserted in this document. Success for the internal hackathon is defined qualitatively first: the flagship workflow completes end-to-end reliably across multiple rehearsal runs; the sovereignty monitor shows zero external activity throughout; the coding and multimodal demos complete without manual intervention; the security and robustness demos behave as designed. Quantitative SIAB figures (§29) are the second layer of evidence, gathered where time permits, never substituted with placeholder numbers presented as real.

---

## 31. Demo Strategy

**Flagship — Inspection Report → Verified Decision Package:**
```
UPLOAD → CLASSIFY → DOCUMENT INTELLIGENCE → OCR/VISION → EVIDENCE OBJECTS →
KNOWLEDGE RETRIEVAL → SOP/MANUAL MATCHING → REASONING → CALCULATION IF REQUIRED →
DETERMINISTIC VERIFICATION → RISK CLASSIFICATION → HUMAN APPROVAL WHERE REQUIRED →
ARTIFACT GENERATION → PROVENANCE/AUDIT → SOVEREIGNTY MONITORING
```

**Correction #1 applied — R8 resolved.** Outputs (`DECIDED`):
```
Inspection Decision Package
├── Decision_Note.docx     — the approval note / decision package
├── Inspection_Data.xlsx   — structured readings, thresholds, status, evidence refs
└── Evidence_Report.pdf    — evidence and provenance detail
```
`Inspection_Data.xlsx` minimum workbook structure: one row per measurement, columns = `measurement, current_value, threshold, status (pass/fail/margin), evidence_reference (Evidence Object ID)`. This gives R8 a concrete, non-optional demo moment rather than an unimplemented traceability-matrix entry — resolving the gap the Review identified (no demo previously exercised R8 at all).

**Secondary demos**, all running through the same execution fabric, not built as separate products:
- **Demo 2 — Coding Agent:** task → model selection → generation → sandbox execution → test → failure detection → self-correction → verified output.
- **Demo 3 — Multimodal Understanding:** image/P&ID-style diagram/handwritten note → vision model → evidence → reasoning → explanation.
- **Security demo:** a document containing embedded injected instructions → detected, blocked, legitimate workflow continues.
- **Robustness demo:** conflicting evidence (SOP vs. historical vs. current reading) → surfaced explicitly, not silently averaged.
- **Sovereignty demo:** live network monitor running concurrently with all of the above, external connections/DNS/cloud calls at zero throughout.

---

## 32. Technology Decision Matrix

| Technology | Category | Candidate(s) | MVP status | Decision | Alternatives | Hardware impact | License | Fallback |
|---|---|---|---|---|---|---|---|---|
| Frontend | UI | Next.js/React/TS | PREFERRED | PENDING confirm | — | None | OSS | — |
| Backend | API | FastAPI/Python | PREFERRED | PENDING confirm | — | None | OSS | — |
| Inference runtime | Model serving | Ollama vs vLLM | **BAKE-OFF** | PENDING | Both viable | Ollama simpler VRAM mgmt; vLLM better throughput/native tool-calling | OSS | Ollama if inconclusive |
| Agent runtime | Orchestration | LangGraph vs custom | **BAKE-OFF** | PENDING | Both viable | None significant | OSS | Custom minimal state machine |
| Document pipeline | OCR/layout | Docling vs PaddleOCR PP-StructureV3 | **BAKE-OFF** | PENDING | Both viable | Moderate | OSS | Whichever clears the quality bar first |
| Retrieval/DB | Hybrid search | PostgreSQL+pgvector | DECIDED (MVP) | DECIDED | OpenSearch (deferred) | Low | OSS | — |
| Sandbox | Isolation | Rootless Docker | PREFERRED | PENDING (OS-dependent) | — | Low | OSS | — |
| Sovereignty enforcement | Network | OS-specific (nftables/WFP/etc.) | **BAKE-OFF** | PENDING | See §25 candidates | Low | — | Narrower monitor scope if full capture proves unreliable |
| Evaluation | Benchmark | Custom SIAB harness + Ragas/DeepEval metrics | PREFERRED | PENDING | — | Low | OSS | — |
| Orchestration infra | Scale-out | Kubernetes/Kafka/mesh | DEFERRED | DECIDED (not used) | — | High | — | — |

Exact model names are intentionally not locked here — see §15 and §37; no model family is selected without bake-off evaluation.

---

## 33. Hardware / Deployment

`CONFIRMED` development/demo baseline: Intel i7-14700HX, RTX 4060 (8 GB VRAM), 16 GB DDR5 RAM. `PROPOSED` deployment scaling path (structural, not yet built): workstation → single-GPU server → multi-GPU server → enterprise cluster, achieved by adding registry entries and adjusting resource-optimizer thresholds — no application-logic redesign required. This path is a credibility statement about the architecture, not an MVP deliverable.

---

## 34. MVP Scope

`DECIDED`, revised for the five-day remaining window:

| Priority | Scope |
|---|---|
| **P0 — must work** | Local multi-model inference (2–3 model roles); registry + deterministic router; document ingestion + OCR/vision; hybrid retrieval; Evidence Objects (normalized-coordinate format); agent state machine; P0 tool set including `create_xlsx`; sandbox; verification fabric (all 8 checks); risk tiers + 3-role identity + approval; DOCX **and** XLSX artifacts with structural+semantic validation; audit trail; live sovereignty monitor; 3-configuration SIAB run |
| **P1 — important, time-permitting** | PPTX/PDF artifact formats; richer evidence explorer; benchmark dashboard polish; additional SIAB baselines |
| **P2 — post-hackathon** | Lightweight knowledge graph; ablation SIAB configs; additional agent types; broader workflows |
| **P3 — future/enterprise** | SCADA/ERP/CMMS integration; multi-GPU orchestration; production-scale connectors; enterprise SSO |

**Never cut:** the flagship demo, the verification fabric, the sovereignty monitor, the XLSX output. **Cut first if time is short:** P1 artifact formats → additional SIAB configs beyond the 3 P0 → dashboard polish → richer evidence explorer UI.

---

## 35. Remaining Timeline (7–12 September)

The original nine-day plan (from 3 September) is stale. `DECIDED` — five real days remain.

| Date | Focus |
|---|---|
| **7 Sep (today)** | Close all bake-off decisions (§37) with a hard cutoff time; finalize capability taxonomy, identity model, and Evidence Object format in code; scaffold repo |
| **8 Sep** | Model registry + router (deterministic, per §14); document intelligence pipeline on real sample scans; Evidence Objects wired to OCR/vision output |
| **9 Sep** | Hybrid retrieval; agent state machine; core P0 tool registry; sandbox stood up and timeout-validated against the real coding-demo task |
| **10 Sep** | Verification fabric (all 8 checks, rule-specific tolerances); risk classification + approval gate (3-role identity); artifact engine (DOCX **and** XLSX, structural+semantic validation) |
| **11 Sep** | Sovereignty monitor (validated mechanism from 7 Sep); full end-to-end flagship rehearsal; coding + multimodal + security + robustness demo scripts; 3-config SIAB run |
| **12 Sep (demo day)** | Final rehearsal under time pressure; bug triage; scope freeze; judge Q&A prep |

**Already completed (as of 7 Sep):** problem-statement analysis, competitive research, architecture design, PRD v1.0, Technical Architecture Specification v0.1, PRD-vs-Architecture Review, Team Research & Strategy Dossier. **Remaining validation:** the entire bake-off set (§37). **Remaining implementation:** everything in §34's P0 list. **Demo freeze:** end of day 11 September — no new P0 scope after that point.

---

## 36. Team Responsibilities

`PROPOSED` five tracks (product-level ownership; implementation module boundaries — `domain, model_gateway, router, agent, document_intelligence, retrieval, evidence, tools, verification, policy, artifacts, sovereignty, evaluation` — remain defined in the Technical Architecture Specification, not restated here):

| Track | Owns |
|---|---|
| A — Frontend/UX | Workbench, task execution view (with routing rationale display), evidence explorer, sovereignty dashboard, approval UI embedded in `/tasks/:id` |
| B — Backend/orchestration | APIs (per the single inventory, §28), task manager, agent state machine wiring |
| C — Models/routing | Registry, canonical capability taxonomy, adapters, deterministic router, benchmark profile fields |
| D — RAG/document intelligence | Ingestion, OCR/vision, Evidence Objects, hybrid retrieval |
| E — Security/sandbox/SIAB | Tool registry, policy engine, 3-role identity, sandbox, sovereignty enforcement/monitor, SIAB harness (3-config P0) |

---

## 37. Bake-Off / Open Decisions

`PENDING`, must close on 7 September with a hard cutoff time and pre-agreed fallbacks:

| Decision | Owner | Candidates | Test | Success criteria | Fallback |
|---|---|---|---|---|---|
| Actual demo OS | E | Native Linux / Windows+WSL2 | Confirm and document | Confirmed | N/A — must be known first |
| Actual usable VRAM | C | Measure, don't assume | `nvidia-smi` baseline + loaded-model measurement | Matches/exceeds nameplate minus overhead | Plan around measured figure |
| Inference runtime | C | Ollama vs vLLM | Stand up both on sample models | Setup time, stability, tool-calling support | Ollama |
| Vision model | C/D | 2–3 candidates | OCR/vision quality on real sample scans | Clears minimum accuracy bar within VRAM budget | Smallest model clearing the bar |
| Reasoning model | C | 2–3 candidates | Planning quality on sample tasks | Coherent multi-step plans | Smallest model clearing the bar |
| Coding model | C/E | 1–2 candidates | Code gen + sandbox execution on sample task | Passes chosen demo task | Simplify demo task |
| Embedding model | C/D | 1–2 candidates | Retrieval quality on sample KB | Acceptable relevance | Any OSS embedding model clearing a minimum bar |
| Concurrent vs. swap strategy | C | Load candidates together, measure VRAM | Combined VRAM vs. budget | Confirms feasibility | Sequential swap + visible switching UI |
| Document pipeline | D | Docling vs PaddleOCR | Run both on real sample scans | Table/OCR/layout fidelity | Whichever clears the bar first |
| Retrieval approach | D | PostgreSQL FTS+pgvector | Hybrid search on sample KB | Acceptable relevance, no added infra | PostgreSQL+pgvector (already decided, §17) |
| Agent runtime | B | LangGraph vs custom | Build flagship flow in both, time-boxed | Further along by cutoff | Custom minimal state machine |
| Sovereignty enforcement | E | Per §25 candidate list | Attempt external call, confirm block+log | 100% block, visibly logged live | Narrower monitor scope |
| XLSX generation method | D/E | Direct library vs templated renderer | Generate `Inspection_Data.xlsx` from sample data | Opens correctly, required fields present | Fewer columns if needed |

**Decision rule (`DECIDED`):** select the smallest stack that (1) satisfies P0, (2) fits *measured*, not assumed, hardware, (3) is reliable across repeated runs, and (4) is debuggable under time pressure.

---

## 38. Testing

Unit tests (tool/service correctness) · integration tests (model gateway, RAG, agent, sandbox) · workflow tests (full flagship run) · **security tests** (prompt injection, unauthorized tool calls, unexpected network access — tested against the 3-role identity model) · benchmark tests (3-config SIAB) · failure tests (model unavailable, OCR failure, tool failure, retrieval failure, validation failure, artifact-generation failure) · demo rehearsal (repeated, timed, judge-like conditions on 11–12 September).

---

## 39. Acceptance Criteria

`DECIDED`, testable form, tied to the Definition of Done pattern (§40):

- The system shall report end-to-end task latency and per-model/per-tool timing for every completed workflow.
- Unauthorized tool calls (per the ENGINEER/APPROVER/ADMIN role model) shall be blocked by the policy layer and recorded in the audit log.
- Document extraction accuracy shall be evaluated against a manually annotated sample and reported via SIAB.
- A prompt-injection payload embedded in an uploaded document shall not alter agent tool-call behavior; the attempt shall be logged.
- Zero external network connections shall be recorded during the full flagship demo run, shown live on the sovereignty dashboard.
- Every AMBER/RED action shall require an explicit APPROVER-role approval event before artifact delivery, recorded in the audit trail.
- `Inspection_Data.xlsx` shall open without corruption and contain all required columns (measurement, current_value, threshold, status, evidence_reference) for every row in the demo dataset.
- Every artifact shall pass both structural and semantic validation (§27) before being presented as complete.

---

## 40. Risk Register

| Risk | Probability | Impact | Mitigation | Fallback |
|---|---|---|---|---|
| VRAM limitations on demo hardware | High | High | Measure real VRAM on 7 Sep; quantized small models | Sequential swap only |
| Model latency during live demo | Medium | High | Pre-warm required models | Pre-recorded fallback run |
| Model switching overhead | Medium | Medium | Track switch latency; honest "switching" UI state | Fewer distinct model roles |
| Hallucination in reasoning output | High | Medium | Evidence-first reasoning + verification fabric | Flag unsupported claims explicitly |
| OCR errors on poor scans | Medium | Medium | Curate demo documents; bake-off on real samples | Show error-handling path as a feature |
| Retrieval errors | Medium | Medium | Hybrid retrieval + retrieval verification | Evidence panel surfaces errors, doesn't hide them |
| Prompt injection success | Low (if built per §24) | High | Explicit trust-boundary architecture, tested | Disable affected tool path, alert reviewer |
| Sandbox escape | Low | High | Rootless Docker, no network, resource limits | Kill switch, isolated demo VM |
| Sovereignty enforcement failure | Medium (OS-dependent) | High | Validate mechanism on actual OS on 7 Sep | Narrower monitor scope, honestly disclosed |
| Malformed artifact output | Medium | Low | Structural + semantic validation (§27) | Regenerate with stricter template |
| Demo instability under time pressure | Medium | High | Rehearsals 11–12 Sep | Recorded backup demo |
| Scope creep | High | High | Hard P0/P1/P2/P3 boundaries (§34), daily enforcement | Cut P1 first, never P0 |
| Benchmark over-scoping | Medium | Medium | 3-config P0 cut (§29) | Report honestly what was/wasn't run |
| Compressed timeline (5 days vs. original 9) | High | High | Tight bake-off cutoff on 7 Sep; freeze scope 11 Sep | Reduce demo breadth before reducing verification fabric |

---

## 41. Traceability Matrix

`DECIDED` — final form; no mandatory requirement is "implicitly satisfied."

| PS Req | Product Requirement | Architecture | P0? | Implementation | Test | Demo Evidence |
|---|---|---|---|---|---|---|
| R1 | Air-gapped, on-prem | Infrastructure Layer, default-deny network | Yes | Docker/host network policy (§37) | External-call block test | Sovereignty demo, live monitor |
| R2 | Multiple open-weight models | Model Plane registry | Yes | 2–3 model roles registered | Router candidate-selection test | Different models selected across demos |
| R3 | Automatic model selection | Control Plane router (§14) | Yes | Deterministic capability+resource scoring | Routing unit test | Execution trace shows routing rationale |
| R4 | Extensible without redesign | Registry + adapter interface | Yes | New registry entry = new model | N/A (structural) | Explained live if asked |
| R5 | Genuine agentic behavior | Agent state machine (§18) | Yes | Plan-act-observe-verify loop | Multi-step workflow test | Flagship + coding demo |
| R6 | Local file read/write | Tool Plane (§19) | Yes | `structured_file_read/write` | Tool schema test | Flagship demo |
| R7 | Sandboxed code execution | Sandbox (§20) | Yes | Rootless Docker, no network | Unauthorized-access test | Coding demo |
| R8 | Spreadsheet work | Artifact Engine + `create_xlsx` (§19, §31) | **Yes (corrected)** | XLSX tool + workbook schema | Workbook validity + field-presence test | `Inspection_Data.xlsx` in flagship demo |
| R9 | Internal knowledge search | Knowledge/RAG Plane (§17) | Yes | Hybrid retrieval | Retrieval relevance test | SOP/manual matching in flagship demo |
| R10 | Multimodal understanding | Document Intelligence + vision models (§16) | Yes | OCR/VLM pipeline | Extraction accuracy test | Flagship + multimodal demo |
| R11 | Local OCR/vision | Document Intelligence Plane | Yes | On-device OCR/VLM | Same as R10 | Same as R10 |
| R12 | Real deliverables | Artifact Engine (§26) | Yes | DOCX+XLSX+PDF generation | Structural+semantic validation test | Full Decision Package |
| R13 | Visible zero-egress proof | Sovereignty Plane (§25) | Yes | Egress enforcement + live monitor | External-call block test | Sovereignty demo, live throughout |

---

## 42. ADR Index

| ADR | Title | Status |
|---|---|---|
| ADR-001 | MVP architecture style (modular monolith + isolated execution service, no Kubernetes/Kafka) | DECIDED |
| ADR-002 | Inference runtime (Ollama vs. vLLM) | PENDING — bake-off 7 Sep |
| ADR-003 | Model/capability taxonomy (§15 canonical enums) | DECIDED |
| ADR-004 | Model family/version choice | PENDING — bake-off 7 Sep |
| ADR-005 | Document intelligence pipeline (Docling vs. PaddleOCR) | PENDING — bake-off 7 Sep |
| ADR-006 | Retrieval architecture (PostgreSQL+pgvector) | DECIDED |
| ADR-007 | Agent runtime (LangGraph vs. custom) | PENDING — bake-off 7 Sep |
| ADR-008 | Sandbox (rootless Docker) | PENDING — confirm on target OS |
| ADR-009 | Sovereignty enforcement mechanism | PENDING — bake-off 7 Sep |
| ADR-010 | Artifact engine (structural+semantic validation model) | DECIDED |
| ADR-011 | Benchmark methodology (3-config P0 SIAB) | DECIDED |
| ADR-012 | MVP spreadsheet integration (`Inspection_Data.xlsx` in flagship) | DECIDED |
| ADR-013 | Minimal identity model (ENGINEER/APPROVER/ADMIN) | DECIDED |
| ADR-014 | Approval UI placement (embedded in `/tasks/:id`) | DECIDED |

---

## 43. Judge Q&A

**Does this already exist?** Partially — individual capabilities exist across public and commercial products, including a public repo targeting this exact PS. What we haven't found elsewhere is the verification-first fabric wrapped around capability-aware routing, backed by an adversarially-tested benchmark.

**What is unique?** Not any single component — the combination of capability-aware routing, evidence-native reasoning, deterministic verification alongside LLM judgment, risk-adaptive autonomy, and demonstrated (not asserted) sovereignty, applied structurally.

**Why not Open WebUI / AnythingLLM / Dify / OpenHands?** These solve real pieces of the problem well — private chat/documents, workflow orchestration, sandboxed coding agents. SAFIRE's unit of interaction is a risk-classified, evidence-native task pipeline with mandatory verification and provenance, not a conversation or a manually-built workflow.

**Why not Cognite / Siemens?** Credible industrial-domain platforms; `INFERENCE` typically cloud- or vendor-infrastructure-tied, which conflicts with the air-gap requirement as a direct substitute.

**Why not Sarvam / NVIDIA / Dell / HPE?** These operate at the sovereign-infrastructure layer, one level below SAFIRE. SAFIRE is an application-level execution fabric that could plausibly run on such infrastructure, not a competitor to it.

**Why not just run Qwen (or any single model) locally?** A single model can't simultaneously be best at OCR, reasoning, and coding without paying an unnecessary VRAM/latency cost for the tasks that don't need it — a real constraint on this hardware (§15, §33).

**Why multiple models? How does routing work?** Different tasks need different capability profiles; routing is a deterministic, explainable scoring process (§14) — capability fit, resource fit, latency fit, measured quality, and risk — never an opaque learned policy in the MVP.

**How much faster/more accurate/cheaper are you? How do you prove it?** `TO BE VALIDATED` via SIAB (§29) — three P0 comparison configurations, reported as a table with placeholders until measured. No number is claimed before it's run.

**How do you prevent hallucinations?** Evidence-first reasoning (§21) plus the verification fabric's evidence and calculation checks (§22) — unsupported claims are flagged, not silently delivered.

**How do you stop prompt injection?** An explicit untrusted-content trust boundary (§24) — tested directly in the security demo (§31).

**How do you stop unauthorized tool execution?** The 3-role identity model (§24) plus per-tool permission and risk classification (§19) — tested directly against acceptance criteria (§39).

**How do you prove zero egress?** A live network monitor covering the actual application process tree — not just the sandbox — running throughout the demo, showing zero external connections/DNS/cloud calls (§25, §31).

**What happens if a model fails?** The Escalation Manager falls back to the next-best available model and flags reduced confidence, rather than failing silently (§14).

**What happens if VRAM is insufficient?** Sequential model swapping with a visible "switching model" state — this is the guaranteed fallback, not an edge case (§15).

**Can this run on the available hardware?** Yes by design — the PS explicitly allows smaller models when high-end hardware isn't available, and the MVP targets exactly the confirmed RTX 4060 workstation (§33).

**Can new models be added later?** Yes — a new registry entry with a capability declaration; no application-logic change (§15).

**Can it control refinery equipment?** No — explicitly a non-goal (§6, §23); no RED-tier tool has operational-system write access, and consequential actions always require human approval.

---

# FINAL TEAM CHECKLIST

Before implementation:

- [ ] mandatory requirements reconciled (§41)
- [ ] spreadsheet P0 (§10, §19, §31 — DECIDED)
- [ ] capability taxonomy fixed (§15 — DECIDED)
- [ ] VRAM strategy resolved (§15 — sequential swap DECIDED as fallback; concurrency PENDING measurement)
- [ ] OS/network strategy resolved (§25, §37 — PENDING, 7 Sep cutoff)
- [ ] model bake-off complete (§37 — PENDING)
- [ ] document bake-off complete (§37 — PENDING)
- [ ] inference runtime selected (§37 — PENDING)
- [ ] retrieval selected (§17 — DECIDED: PostgreSQL+pgvector)
- [ ] minimal identity selected (§24 — DECIDED: ENGINEER/APPROVER/ADMIN)
- [ ] artifact validation defined (§27 — DECIDED: structural + semantic)
- [ ] benchmark P0 reduced (§29 — DECIDED: 3 configs)
- [ ] flagship demo verified (§31 — PENDING rehearsal, 11 Sep)
- [ ] sovereignty proof verified (§25, §37 — PENDING)
- [ ] architecture frozen (§11 — DECIDED: nine-plane architecture unchanged)
