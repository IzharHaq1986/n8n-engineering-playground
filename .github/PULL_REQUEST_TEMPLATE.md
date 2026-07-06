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
