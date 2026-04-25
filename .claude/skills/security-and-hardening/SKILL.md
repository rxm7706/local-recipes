---
name: security-and-hardening
description: Security-first development. Three-tier boundary system: Always Do / Ask First / Never Do. Prevents OWASP Top 10 vulnerabilities.
source: https://github.com/addyosmani/agent-skills
---

# Security and Hardening

## Core Philosophy

Security is a foundational constraint, not an afterthought.

## Three-Tier Boundary System

### Always Do (Non-negotiable)
- Validate all external input at system boundaries (API routes, form handlers)
- Use parameterized queries — never string-interpolated SQL
- Enforce HTTPS everywhere
- Hash passwords with bcrypt/scrypt/argon2, salt rounds ≥ 12
- Set `httpOnly` and `secure` cookie flags

### Ask First (Require explicit approval)
- Modifying auth flows or session handling
- Adding new external integrations or third-party services
- Changing permission models or access control logic
- Storing new categories of sensitive data

### Never Do (Absolute prohibitions)
- Commit secrets, API keys, or credentials to source control
- Trust client-side validation alone
- Use `eval()` or equivalent dynamic code execution on user input
- Use wildcard CORS origins (`*`) in production
- Skip authorization checks — authentication ≠ authorization

## Key Practices

**Input Handling**: Validate at system boundaries; use Zod or equivalent schema validation.

**XSS Prevention**: Leverage framework auto-escaping (React does this by default). Use DOMPurify as fallback when inserting raw HTML.

**Access Control**: Every endpoint must verify the user has permission for *that specific resource*, not just that they're logged in.

**Dependency Audits**: Check `npm audit` / `pip audit` contextually:
- Critical vulnerabilities in reachable code → fix immediately
- Dev-only or unreachable vulnerabilities → schedule fix

## Red Flags

- Secrets in code or environment files committed to git
- Missing authorization checks on endpoints
- Wildcard CORS origins
- Unvalidated user input flowing into databases or HTML rendering
- `eval()` anywhere near user-controlled data

## Conda-Forge Application

Apply to the `scan_for_vulnerabilities` step and CVE resolution:

**Always Do in recipes:**
- Pin away from known-CVE versions (check OSV.dev findings)
- Never include test/dev dependencies in `run` requirements
- Validate all source URLs and checksums (sha256)

**Ask First:**
- Loosening version pins due to unavailability (document with TODO to re-tighten)
- Adding a new dependency with no conda-forge equivalent

**Never Do:**
- Ignore Critical or High CVE findings without documenting why
- Pin to a version known to have an actively exploited vulnerability
- Include secrets or tokens in recipe files
