# Simplenote MCP Server – Roadmap & Release Prep (Updated 2025-08-11)

This document captures the current actionable roadmap distilled from the recent CI/CD audit, project review, and outstanding improvement opportunities. It replaces the historical status log with a forward-looking, execution‑oriented plan aimed at the next release.

---
## 🎯 Next Release Objective

Deliver a reliability & security focused release (vNEXT) that:

- Expands CI from smoke test → full test suite with coverage artifact
- Introduces authenticated supply‑chain vulnerability scanning in core CI
- Produces durable changelog artifacts during automated releases
- Lays groundwork for future quality gates (evaluation & security)

---
## ✅ Quick Wins (Implemented Now)

These items are being committed together with this roadmap update:

- [x] CI: Run full pytest suite (not just `test_main_module.py`)
- [x] CI: Generate coverage XML + upload artifact
- [x] CI: Add dependency vulnerability scan (pip-audit) & artifact
- [x] Release: Commit and ship `changelog.md` + upload as artifact
- [x] Tooling: Add `pip-audit` to dev / all extras for reproducible scanning

---
## 🧪 Testing & Quality (Near-Term)

- [x] Add minimal coverage threshold gate (e.g. 70%) – optional, non-blocking first
- [ ] Add focused cache edge case tests (expiry race, negative TTL)
- [ ] Add end-to-end user session scenario (create → tag → search → paginate → delete)
- [ ] Mark long-running performance tests with `@pytest.mark.perf` and exclude from default
- [ ] Introduce structured test matrix grouping (unit | integration | perf) via pytest markers

### Medium

- [ ] Raise `tool_handlers.py` coverage toward 80% (target +18%)
- [ ] Batch operation simulation tests (bulk create/update)

---
## 🔐 Security & Supply Chain

### Quick / In Flight

- [x] pip-audit integrated in CI (report artifact)

### Short Term

- [ ] Fail pipeline on HIGH severity vulnerabilities (phase 2 – currently informational)
- [ ] Add SBOM generation (e.g. `pip-audit -r` / `cyclonedx-py`)
- [ ] Add credential rotation playbook docs
- [ ] Session/auth timeout mechanism & test

### Medium

- [ ] CodeQL static analysis workflow
- [ ] Authorization boundary & abuse case tests
- [ ] Alerting hook for suspicious pattern logs

---
## 🛠 CI/CD & Automation

### Implemented

- [x] Unified Python 3.12 (except matrix) / version pin drift resolved
- [x] Weekly schedule rationalization & timeouts added
- [x] Full test + coverage + audit integrated

### Next

- [ ] Consolidate lightweight scheduled badge + security monitoring into a single workflow
- [ ] Add evaluation result-based quality gate (non-blocking pilot)
- [ ] Cache pip & build artifacts between matrix jobs (actions/cache key refinement)
- [ ] Introduce coverage badge automation (post CI job)

---
## 📦 Release Engineering

### Implemented

- [x] Changelog artifact + committed changelog in release workflow

### Next

- [ ] Conventional commit parsing to improve changelog categorization
- [ ] Pre-release dry-run workflow that diff-checks dependency changes
- [ ] Signed git tags (GPG / Sigstore) integration
- [ ] Publish SBOM + vulnerability report as release assets

---
## 📊 Observability & Performance

- [ ] Standardize logging schema (add logger factory + contextual fields)
- [ ] Optional HTTP health & metrics endpoint (readiness / liveness probes)
- [ ] Latency histogram & cache efficacy metrics
- [ ] Performance regression alert threshold definition

---
## 🧩 Architecture & Code Quality

- [ ] Extract repeated error formatting into shared helper
- [ ] Normalize exception taxonomy & user-facing messages
- [ ] Introduce thin service layer for note operations (separating transport vs logic)

---
## 🗂 Documentation & Community

- [ ] Author evaluation best-practices guide
- [ ] Contributor guide for adding new evaluation scenarios
- [ ] Troubleshooting matrix (CI failures → probable causes)

---
## 🌱 Future (Backlog / Post-Release)

- Note templates & snippets
- Advanced regex search
- Webhook support for note lifecycle events
- Usage metrics + dashboard
- Plugin/extensibility framework exploration

---
## ⏱ Execution Phasing

Phase 0 (THIS COMMIT): Quick wins (complete)
Phase 1 (Days 1–3): Coverage gating (soft), cache edge tests, consolidated scheduled workflow draft
Phase 2 (Week 2): SBOM + CodeQL + auth timeout + structured logging
Phase 3 (Week 3): Release enhancements (conventional commits, SBOM assets)
Phase 4 (Week 4+): Feature backlog initiation (regex search, templates)

---
## 📌 Metrics Targets (Next Release)

- CI success rate ≥ 97%
- Coverage ≥ 75% maintained (no regression) & per-module trend tracking
- Zero HIGH / CRITICAL vulnerabilities at merge time
- Mean test runtime ≤ 5 min for full matrix (optimize if exceeded)

---
Last Updated: 2025-08-11
Owner: Core Maintainers
Next Review: 2025-09-01
