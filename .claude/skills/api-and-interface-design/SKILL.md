---
name: api-and-interface-design
description: Principles for creating stable, usable interfaces across REST APIs, GraphQL schemas, module boundaries, and component contracts.
source: https://github.com/addyosmani/agent-skills
---

# API and Interface Design Guide

## Key Foundational Concepts

**Hyrum's Law**: "With a sufficient number of users of an API, all observable behaviors of your system will be depended on by somebody, regardless of what you promise in the contract." Treat every observable behavior—including undocumented quirks and error messages—as a de facto commitment.

**One-Version Rule**: Avoid scenarios where consumers must choose between multiple versions of the same dependency, preventing diamond dependency problems.

## Five Core Principles

1. **Contract First** — Define interfaces before implementing them; the contract is your specification
2. **Consistent Error Semantics** — Use one error strategy everywhere (e.g., HTTP status codes with structured error bodies)
3. **Validate at Boundaries** — Trust internal code but validate rigorously where external input enters systems
4. **Prefer Addition Over Modification** — Extend interfaces with optional fields rather than changing existing ones
5. **Predictable Naming** — Plural nouns for REST endpoints, camelCase for fields, UPPER_SNAKE for enums

## Implementation Patterns

- Resource-oriented REST endpoints with pagination and filtering
- TypeScript: discriminated unions, input/output separation, branded types
- Validate third-party API responses as untrusted data

## Verification Checklist

- [ ] Typed schemas defined
- [ ] Consistent error format
- [ ] Boundary validation in place
- [ ] Pagination supported
- [ ] Changes are backward-compatible

## Red Flags

- Breaking changes without versioning
- Inconsistent error shapes across endpoints
- Trusting external API responses without validation
- Removing fields that consumers may depend on
