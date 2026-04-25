---
name: idea-refine
description: Transform raw concepts into actionable plans via three phases: divergent thinking, convergence, and sharpening.
source: https://github.com/addyosmani/agent-skills
---

# Idea Refine

## Core Process

### Phase 1: Understand & Expand (Divergent Thinking)

1. Restate the idea as a "How Might We" problem statement
2. Ask 3–5 sharpening questions:
   - Who is the target user?
   - What does success look like (metric)?
   - What are the constraints?
   - Why now?
3. Generate 5–8 variations using lenses: inversion, constraint removal, audience shifts, simplification

### Phase 2: Evaluate & Converge

1. Cluster ideas into 2–3 meaningful directions
2. Stress-test each against: user value, feasibility, differentiation
3. Surface hidden assumptions
4. Identify what could undermine each direction

### Phase 3: Sharpen & Ship

Produce a markdown one-pager with:
- Recommended direction
- Key assumptions to validate first
- MVP scope
- **"Not Doing" list** — make trade-offs transparent

## Key Philosophy

> "Simplicity is the ultimate sophistication."

- Understand the user experience first, then work backward to technology
- Focus over breadth
- Challenge conventional approaches

## Critical Success Factor

The **"Not Doing" list** is arguably the most valuable part. Explicitly saying no to good ideas that don't align with the focused direction prevents scope creep.

## Conda-Forge Application

Apply before packaging a new library:
- **HMW**: "How might we package X so conda-forge users can install it without dependency conflicts?"
- **Assumptions to validate**: Does a conda-forge package already exist? Is the license compatible? Are all deps available on conda-forge?
- **Not Doing**: Don't package optional extras unless they're commonly needed; don't create multi-output recipes unless the package is genuinely split upstream
