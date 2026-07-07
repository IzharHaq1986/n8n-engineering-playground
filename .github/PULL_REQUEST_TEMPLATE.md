# Pull Request

## Summary

Briefly describe the change.

## Pre-Flight Checklist

### 1) Scope Control

- [ ] This is the next step only
- [ ] Change is minimal and reviewable
- [ ] No unrelated files are being modified
- [ ] No unnecessary abstraction is being introduced

### 2) Architecture Fit

- [ ] Existing repository structure is preserved
- [ ] Existing interfaces and behavior remain intact unless intentionally changed
- [ ] Existing modules and functions are reused where appropriate
- [ ] Change aligns with current project_state.md direction

### 3) Code Quality

- [ ] Code is readable, minimal, and clean
- [ ] Comments are helpful and concise
- [ ] Error handling remains explicit and predictable
- [ ] No local artifacts or temporary files are included

### 4) Guardrails and Safety

- [ ] Inputs remain validated and sanitized
- [ ] Trusted and untrusted context remain separated
- [ ] High-risk behavior is not introduced without explicit gating
- [ ] Change reduces real risk or ships real value

### 5) Practical Filter

- [ ] This will still matter in 30–60 days
- [ ] This can not be reasonably deferred or dropped
- [ ] This does not add confusion where attention is scarce

### 6) Validation

- [ ] Lint will pass
- [ ] Tests will pass
- [ ] CI behavior is considered before pushing
- [ ] Change is ready for PR review

### 7) AI Engineering Review

- [ ] AI output has been verified for correctness and completeness
- [ ] Security implications have been reviewed
- [ ] Edge cases and failure modes have been considered
- [ ] Tests and deterministic behavior have been considered
- [ ] Logging and auditability remain sufficient
- [ ] High-risk actions require explicit human approval
- [ ] Change aligns with architecture, coding standards, and long-term maintainability

#### Engineering Principle

Treat AI as an engineering assistant, not the final decision-maker.

Engineers remain responsible for the system's safety, reliability, security, and production outcomes.

---

### 8) AI Agent Systems

- [ ] APIs remain stable, documented, and machine-friendly
- [ ] Security follows least privilege and explicit authorization
- [ ] High-risk actions require human approval
- [ ] All agent actions are logged and auditable
- [ ] Systems remain deterministic, observable, and recoverable
- [ ] Components remain modular and avoid unnecessary vendor lock-in

#### Engineering Principle

Design systems assuming trustworthy AI agents will increasingly become system users.

---

### 9) AI Architecture

- [ ] AI systems remain model-agnostic where practical
- [ ] Multimodal requirements are considered where appropriate
- [ ] The smallest suitable model is preferred
- [ ] Functional, latency, cost, privacy, and reliability requirements are balanced
- [ ] AI components remain modular so models can be replaced without major architectural changes

---

### 10) AI Planning and Validation

- [ ] Objective is clearly defined
- [ ] Constraints are documented
- [ ] Acceptance criteria are defined
- [ ] Required context has been identified
- [ ] Complex work is separated into planning, implementation, testing, and review
- [ ] AI output is treated as a draft and independently validated before acceptance

