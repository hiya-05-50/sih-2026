# ADR-001: Sovereign Host OS & Sandbox Enforcement Mechanism

## Status
**Accepted / Locked** (Sprint 2 Milestone)

## Context & Problem Statement
SAFIRE requires a fully air-gapped, zero-leakage execution environment capable of running LLM inference, document OCR, evidence parsing, and untrusted code execution. The deployment target must guarantee hard resource boundaries (VRAM, CPU, Memory) on localized hardware (specifically the reference RTX 4060 8GB VRAM system).

## Decision Drivers
1. **Air-gapped Isolation**: Absolute zero network egress during task/code execution.
2. **Deterministic Resource Limits**: Hard caps on VRAM (6GB max allocated to model containers, leaving 2GB for OS/UI), CPU (8 cores), and RAM (16GB).
3. **OS Parity & Portability**: Native execution on Linux (Ubuntu 24.04 LTS) with full WSL2 compatibility for developer workstations under Windows.
4. **Rootless Security**: Non-root container runtime preventing privilege escalation.

## Considered Options
1. **Option 1: Bare-metal Systemd Cgroups + AppArmor**
2. **Option 2: Rootless Docker Containers with Cgroup v2 & `--net=none` (Chosen)**
3. **Option 3: Full QEMU/KVM Virtual Machines**

## Decision Outcome
**Chosen Option: Option 2 — Rootless Docker Containers with Cgroup v2 & `--net=none`**

### Rationale
- **Host OS**: Ubuntu 24.04 LTS (Kernel 6.8+ with native cgroup v2 enabled). Development supported via Windows WSL2 (Ubuntu kernel).
- **Network Sovereignty**: Sandbox containers executed with `--net=none` flags, physically disabling network sockets.
- **Resource Enforcement**:
  - `memory = "16g"`
  - `cpus = "8.0"`
  - `device_requests = [DeviceRequest(count=-1, capabilities=[['gpu']])]` with VRAM allocation managed by Ollama/vLLM backend boundaries.
- **Rootless execution**: Container daemon executes under unprivileged UID namespace (`dockerd-rootless.sh`).

## Consequences
- **Positive**: Complete air-gapped security, zero privilege escalation vector, strict hardware bounds.
- **Negative**: GPU pass-through in rootless Docker requires `nvidia-container-toolkit` rootless setup on host setup scripts (handled in Sprint 5 setup scripts).
