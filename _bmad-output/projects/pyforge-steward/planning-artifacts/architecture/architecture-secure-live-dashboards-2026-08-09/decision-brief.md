# Where the pattern lives, and what it refuses to decide for you

Companion to `ARCHITECTURE-SPINE.md`. The spine is the build contract; this is the reasoning,
for anyone approving or adopting rather than building.

---

## The delivery question had a forced answer

The Spec asked whether the pattern ships as a `steward` subcommand, a library, or a template
repository. The honest answer is that **it was never one choice**, because the pattern
contains two kinds of work separated by a boundary that cannot be argued with:

| runs | examples | can only be |
|---|---|---|
| **inside** the dashboard's process, per request | role extraction, row filtering, audit write, navigation | a **library** |
| **around** the deployment | container stack, edge policy, WSGI topology, security CI | a **subcommand** |

A subprocess cannot filter a dataframe mid-request. A library cannot provision Nginx. Any
single-artifact answer fails one half.

**Template was ruled out on evidence, not taste.** It has no upgrade path — a diverged adopter
never receives a fix, and the Spec's own open question named that as the deciding case — and
it duplicates the genesis-installer role already consolidated into `pyforge-marshal`.

This also settles the Spec's second open question. *Provide or verify?* **Both, split by
half:** the library provides so nobody reimplements isolation; the subcommand verifies so an
adopter who diverged anyway is still caught.

## The Doctor question, decided rather than deferred

You asked the architecture to decide whether verification is Steward's or Doctor's. It is
**Steward's**, with one carve-out.

Charter §6 bars a station from being the final word on **its own** artifact. An adopter's
dashboard belongs to the adopter, not to Steward — so Steward verifying it is not self-grading,
and the Charter objection does not apply.

What decided the rest was coupling. Verification is inseparable from deployment, and
`steward deploy` already exists and already means *dashboard build/reconcile/status*. Routing
the verdict through Doctor would put a **second station in every adopter's deploy path**, so a
Doctor fault would block a deployment. Doctor is also a repo-rooted diagnostic for *this*
factory; making it a runtime dependency of external deployments inverts its role.

It was technically available — Doctor's sources take `target: Path`, so an external directory
is reachable. The objection was never capability.

**The carve-out:** a verdict on whether **Steward's own pattern implementation** is sound —
as opposed to an adopter's use of it — *is* Doctor's, because that case genuinely is Steward
grading itself.

## Four decisions that change what you can ship

**The trusted ingress is declared, and the library refuses to start without it.** Anything
that can reach the app directly can forge the role header. The blueprint made the header
*names* configurable but never defended the boundary. Now an adopter names the ingress the
proxy connects from, and identity headers arriving from anywhere else stop the process. The
pattern does not authenticate a user — it authenticates the *path*. mTLS is the upgrade, not
the entry price.

**Redis is not mandated; shareable-ness is.** A cache that cannot be shared across workers is
refused when workers > 1. The blueprint's own sample paired `FileSystemCache` with a Compose
stack that provisions Redis precisely so four Gunicorn workers share state — under
`--workers 4` that sample does not deliver the property it advertises. A single-worker adopter
keeps an in-process cache.

**Filter-then-search is enforced by API shape, not by a comment.** The library exposes no
entry point that can search the master set. The Spec asked what *enforces* the order; the
answer is that the unfiltered frame is never handed to anything searchable.

**Audit retention has no default, and a deployment without one is refused.** The trail
accumulates per-user activity — simultaneously a compliance asset and a privacy liability. An
unbounded default would silently hoard personal data; a fixed default would impose one
jurisdiction's answer on everyone. So the adopter declares it and the pattern enforces it.

## What this deliberately does not decide

Atlas's migration timing (Atlas owns that board), which alerting sinks ship first (no adopters
yet to demand one), mTLS at the ingress (AD-4's upgrade path), multi-tenant isolation (a
different problem — this isolates *roles* within one organisation), and where a clustered
audit database runs (the adopter's estate, not the pattern's).

## Status

The Spec stays `draft` and Epic 8-style decomposition has **not** happened: this run produced
the spine, not epics. `spec-secure-live-dashboards` remains registered in the
`chain_completeness_check` deferred list, and the reason recorded there — that the packaging
question bounded every capability — is now **answered**, so that registration should be
revisited when the Spec is decomposed.
