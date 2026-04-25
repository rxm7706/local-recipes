---
name: code-review-and-quality
description: Multi-dimensional code review framework. Evaluate across correctness, readability, architecture, security, and performance before merging.
source: https://github.com/addyosmani/agent-skills
---

# Code Review and Quality

## Five Review Axes

1. **Correctness** — Does it work as intended?
2. **Readability** — Can others understand it?
3. **Architecture** — Does it fit the system design?
4. **Security** — Any vulnerabilities?
5. **Performance** — Any bottlenecks?

## Approval Philosophy

> "Approve a change when it definitely improves overall code health, even if it isn't perfect."

Continuous improvement over perfection.

## Change Sizing

- **~100 lines**: Ideal, reviewable in one sitting
- **~300 lines**: Acceptable if logically cohesive
- **~1000+ lines**: Must be split

Splitting strategies: stack sequential changes, group by file, horizontal layering, vertical feature slices.

## Review Process

1. Understand intent and context
2. Review tests first — they reveal coverage and intent
3. Evaluate implementation across the five axes
4. Categorize findings by severity:
   - **Critical**: Must fix before merging
   - **Required**: Should fix
   - **Optional**: Nice to have
   - **Nit**: Minor style issues
   - **FYI**: Informational only
5. Verify testing and verification approaches

## Key Principles

- Respond to reviews within one business day
- Require cleanup before submission, not deferred
- Be honest — avoid rubber-stamping or softening real issues
- Review dependency additions critically — prefer existing solutions
- Address dead code explicitly

## Conda-Forge Application

Apply when reviewing recipes:
- **Correctness**: sha256, version, license
- **Readability**: recipe structure follows conventions
- **Architecture**: noarch vs compiled, output split
- **Security**: no pinned CVE-affected versions
- **Performance**: build script efficiency, unnecessary rebuild triggers
