---
name: frontend-ui-engineering
description: Standards for production-quality UIs. Component architecture, state management, accessibility, avoiding AI aesthetics.
source: https://github.com/addyosmani/agent-skills
---

# Frontend UI Engineering

## Component Architecture

- Colocate related files: component, tests, hooks, types
- Favor composition over configuration
- Keep components focused on single responsibilities
- Separate data fetching from presentation logic

## State Management (simplest approach per scenario)

- `useState`: local UI state
- `Context`: read-heavy global state (theming, auth)
- URL parameters: shareable state
- Server state libraries: remote data

## Avoiding AI Aesthetics

Common AI-generated patterns to reject:
- Purple/indigo everything
- Excessive gradients
- Uniform rounded corners everywhere
- Oversized padding

Instead: use the project's actual color palette, maintain proper visual hierarchy, respect the design system.

## Design System Adherence

- Consistent spacing scales (no arbitrary pixel values)
- Typography hierarchy
- Semantic color tokens rather than raw hex values

## Accessibility Requirements (WCAG 2.1 AA)

- All interactive elements keyboard navigable
- Form inputs and buttons require proper ARIA labels
- Focus management in modals and dialogs
- Meaningful empty and error states
- Color contrast ≥ 4.5:1 for normal text

## Testing Standards

Before marking complete:
- Zero console errors
- Keyboard accessibility verified
- Screen reader compatible
- Responsive at 320px–1440px
- Loading/error/empty states all handled

## Note for Conda-Forge Context

This skill is not directly applicable to recipe packaging. It applies to any web tooling or dashboards built alongside the packaging pipeline.
