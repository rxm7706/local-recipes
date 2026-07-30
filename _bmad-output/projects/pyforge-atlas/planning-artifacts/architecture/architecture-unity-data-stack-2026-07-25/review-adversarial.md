---
title: Adversarial Divergence Review — Unity Data Stack Architecture Spine
reviewer: adversarial
date: 2026-07-25
verdict: changes-requested
---

# Adversarial Divergence Review — Unity Data Stack Architecture Spine

**Target:** `ARCHITECTURE-SPINE.md` (architecture-unity-data-stack-2026-07-25)
**Method:** for each hole, construct two units one level down (a feature, a Package, a Domain
Asset, a Stage config, a task) that each obey every AD-1..AD-20 to the letter, then show the
concrete incompatibility that results when they're built independently by two different teams.
**Result:** **7 holes** found (target was 6). All 7 are genuine letter-vs-spirit gaps — none is a
missing-implementation-detail complaint. Additional lower-severity findings on AD overlap and
unenforceable rules are recorded in §2–3.

---

## 1. The 7 holes

### Hole 1 — Data Product contract format/versioning has no shared shape (AD-15, AD-16)

**Units:** the `customer` domain's `customer_curated_customer_profile_publish` Asset, and the
`cdo` domain's `cdo_consumption_metrics_publish` Asset.

**Letter-compliance:** Both declare owner, Domain, Layer, and update frequency as structured
metadata (AD-15). Both names match `<domain>_<layer>_<entity>_<verb>` with a valid domain and
layer segment (AD-15). Both publish "a schema contract" (AD-15's rule only says *that* a contract
exists, not its format). Both version their contract and evaluate breaking changes against
declared consumers before merge (AD-16).

**Incompatibility:** `customer`'s team describes its contract as a JSON Schema document and
versions it with an integer that increments on any breaking change (`v7`). `cdo`'s team describes
its contract as an Avro schema and versions it with SemVer (`v2.1.0`), reading AD-16's "version
increment" as satisfied by either scheme. Both are letter-compliant. The moment a third Domain
(or a platform-owned consumer-facing tool — Herald's reporting surface, or a generic "contract
diff" check promised implicitly by AD-16's "evaluated against every declared consumer before
merge") needs to validate a consumer's declared dependency against the producer's actual contract
version, it cannot: it needs one schema description language and one version-comparison semantic
to do "is 2.1.0 compatible with what I depend on" versus "is 7 compatible with what I depend on"
generically. AD-16's own enforcement mechanism ("evaluated against every declared consumer before
merge") has no way to be written once and reused, because two conformant contracts are
structurally incomparable.

**Proposed AD (tighten AD-16):**
> **Binds:** FR-52, all Data Products. **Rule:** every Data Product contract is expressed in one
> platform-mandated schema description format, and every contract version is a SemVer string
> compared by one platform-mandated compatibility rule (MAJOR = breaking). A contract in a
> different format, or versioned by a different scheme, fails the Quality Gate at publish time.

---

### Hole 2 — Stage-differentiating controls have no assigned mutation layer (AD-4, AD-20, AD-13)

**Units:** the `production` Stage config (Restricted classification) and the `uat` Stage config
(Deidentified classification), both declared to reference the **same** `runtime` Environment
(permitted — AD-4: "Many Stages may reference one Environment").

**Letter-compliance:** Each Stage record is schema-validated (AD-4). `runtime` composes only what
it names, declares why it exists and what it excludes, has no inherited default dependencies
(AD-13). `production`'s Stage record states "access logging enabled" because it carries restricted
data (AD-20's literal rule: "Stages carrying restricted data have access logging enabled" — a
Stage-level fact).

**Incompatibility:** AD-20's rule is stated as a property of the *Stage*, but access logging is
runtime behavior that has to be materialized *somewhere* — either baked into the shared
`runtime` Environment (a logging middleware Feature) or applied at the deploy-time
reconciliation layer (a GitOps overlay). Nothing in AD-4, AD-13, or AD-20 assigns which. Team A
(owns the `production` promotion path) implements it as an Environment Feature, because that is
the only mechanism that actually changes running code — and now `uat`, sharing `runtime`, silently
inherits restricted-grade logging overhead it never declared needing, and does so *by way of* the
Environment AD-13 said would have "no inherited default dependency set" (true for the *base*
composition, but Team A's Feature is now inherited by every Stage that references `runtime`,
defeating the isolation AD-4 promised by decoupling Stage count from Environment count). Team B
(owns `uat`), reading AD-4 literally, assumed "same Environment ⇒ identical behavior" and never
audited it for Stage-specific mutations smuggled in through the Feature set.

**Proposed AD (new):**
> **AD-21 — Stage-differentiating controls live at the deploy-time overlay, never in the shared
> Environment.** **Binds:** AD-4, AD-20, FR-56, FR-58. **Prevents:** a control required by one
> Stage's Data Classification leaking into every other Stage that happens to share the same
> Environment, silently defeating AD-4's Environment-count saving. **Rule:** any behavior that
> AD-20 requires as a function of a Stage's Data Classification (access logging, network posture)
> is applied by the GitOps overlay for that Stage, never composed into the Environment's Feature
> set. An Environment's materialized behavior is Stage-agnostic by construction; a Feature that
> branches on Stage identity fails the Quality Gate.

---

### Hole 3 — Derived artifacts are not pinned to one Workspace Lock commit (AD-2)

**Units:** Mason's release pipeline generating the **Offline Bundle** for a `win-64` deployable
Environment, and Steward's air-gap delivery pipeline generating the **Exported Lock**
(`pylock.toml`) for the same release's compliance evidence packet.

**Letter-compliance:** Both artifacts are generated *from* the Workspace Lock, never hand-edited
(AD-2). Each pipeline runs its own drift check comparing its artifact against "the Workspace
Lock" and each passes (AD-2's stated gate).

**Incompatibility:** AD-2 never says the derived artifacts must be generated from the *same*
Workspace Lock **commit**. Mason's Offline Bundle build kicks off at T1 against commit A; a
hotfix lands; Steward's Exported Lock build kicks off at T2 against commit B. Each drift check
is satisfied (each artifact matches "the Workspace Lock" as it existed at its own generation
time) — but the two artifacts nominally backing one release/promotion event now describe two
different resolved dependency sets. Combined with AD-11 (SBOM generated from the *built artifact*,
a third independent generation point) and AD-12 (provenance attesting "the top-level inputs"),
the evidence store (AD-12's consumer) can end up holding three artifacts for one release that
don't actually agree with each other — the exact "two lock artifacts... silently disagreeing"
failure AD-2 exists to prevent, reintroduced one layer up through *time* rather than through a
second solver.

**Proposed AD (tighten AD-2):**
> Append to AD-2's Rule: "Every derived artifact produced for a given release or Stage promotion
> — Exported Lock, Offline Bundle, SBOM, provenance — is generated from one Workspace Lock commit
> SHA, and the release record carries that SHA. Each artifact's drift check asserts equality
> against that pinned SHA, not against the Workspace Lock's state at the artifact's own
> generation time. Two derived artifacts backing the same release that resolve to different SHAs
> fail the gate."

---

### Hole 4 — Task-name uniqueness and `<target>` semantics are unconstrained (AD-9)

**Units:** the `customer` domain's cross-cutting behavioral-test task, and the `cdo` domain's
Package-scoped smoke-test task — both named `test-smoke`.

**Letter-compliance:** Both are named tasks in the Workspace (AD-9). Both follow the
Consistency Conventions' `<verb>-<target>` shape for scoped tasks. Both are invoked by CI, not
inlined (AD-9).

**Incompatibility:** the convention table gives `<verb>-<target>` without stating whether
`<target>` is a Package name, a Domain name, or a test **tag** (FR-25's "selectable by tag —
smoke, integration, per-Domain" introduces exactly this third option). Team A (customer)
implements FR-25's tag-slices as Workspace-global aggregate tasks: `test-smoke` runs the smoke
tag across every Package. Team B (cdo), reading `<target>` as "whatever this task is scoped to,"
defines a Package-scoped `test-smoke` under cdo's own manifest that only runs cdo's smoke slice.
Pixi's task namespace is workspace-flat: the two identically-named, differently-scoped tasks
either silently overwrite each other on manifest load order, or (if package-scoped tasks are
namespaced) produce two entities both surfaced to CI under the same display name with different
semantics. Either way, AD-9's own enforcement mechanism — "a parity check enumerates the tasks CI
invokes against the tasks the aggregate gate runs, and fails on divergence" — cannot tell which
`test-smoke` the aggregate gate means, so the parity check itself becomes ambiguous.

**Proposed AD (tighten AD-9 / the Consistency Conventions "Task naming" row):**
> Task names are globally unique across the Workspace. `<target>` in `<verb>-<target>` is always a
> Package name (never a tag, never a Domain). Cross-cutting test-tag slices (FR-25) are expressed
> as an argument/flag on the public verb (`test --tag smoke`), never as a task name of the same
> shape as a Package-scoped task. A name-uniqueness check runs alongside AD-9's parity check and
> fails the gate on collision.

---

### Hole 5 — Two stations can both legitimately claim one machine-checkable capability (AD-17)

**Units:** "Marshal's lock-drift check" and "Atlas's lock-consistency check" — both independently
implementing the AD-2 drift comparison between the Exported Lock/Offline Bundle and the
Workspace Lock.

**Letter-compliance:** AD-17 assigns Marshal "workspace substrate, build orchestration,
governance enforcement" — the lock-drift check is a workspace-substrate governance-enforcement
task, so Marshal's team builds it as a Quality Gate task per AD-9. AD-17 assigns Atlas
"dependency graph, boundary and schema mapping, the data plane's topology" — the lock-drift check
is *also*, read literally, a dependency-graph-boundary consistency check, so Atlas's team,
building out dependency-graph tooling, independently builds its own version as part of "boundary
mapping."

**Incompatibility:** both checks are named tasks (AD-9 doesn't dedupe by station), both are wired
into CI, and both "pass" — but they were written independently and compare different things:
Marshal's checks whole-file hash equality; Atlas's checks only package-name/version tuples (its
dependency-graph tooling doesn't track hashes, because hashes aren't part of "the graph"). A
divergence that changes a hash without changing a version (a re-pinned build, a re-published
wheel under the same version) is caught by one and missed by the other. This is exactly AD-17's
own "Prevents" clause inverted: not an unowned plane, but **one capability with two owners**, each
individually correct under AD-17's prose and only visible as a defect when their outputs are
compared.

**Proposed AD (tighten AD-17):**
> Append to AD-17's Rule: "Station descriptions assign accountability for a *plane*, not for every
> capability whose subject matter touches two stations' remits. Every machine-checkable capability
> listed in the Capability → Architecture Map resolves to exactly **one** implementing station,
> recorded against that capability, not inferred from station prose. A capability two stations
> both build independently is a defect at the same severity as an unowned one."

---

### Hole 6 — "Owner" has no shared identity shape across planes (AD-7, AD-15, cross-plane)

**Units:** a Package manifest's `owner`/Trusted Committer field (FR-5, workspace plane) and an
Asset's `owner` metadata field (FR-51, data plane).

**Letter-compliance:** Every Package "resolves an owner and a Trusted Committer" (FR-5). Every
Asset "declares owner, domain, layer, and update frequency as structured metadata" (FR-51/AD-15).
Neither AD-7 (dependency direction / Domain peers) nor AD-15 (Data Product discovery) constrains
what shape `owner` takes — both features are separately, correctly satisfied.

**Incompatibility:** Marshal's workspace-substrate tooling (owning FR-5 per AD-17) represents
`owner` as a team slug (`team-customer-eng`) because that's what Trusted-Committer auto-request-
as-reviewer (FR-33) needs — a GitHub-resolvable handle. Atlas's data-plane tooling (owning FR-51
per AD-17) represents `owner` as an individual's email, because Data Mesh ownership in the
research base is person- or role-accountable, not team-accountable. Both are internally
consistent and correct for their own consumer. The moment a cross-plane capability needs both —
FR-38's contribution/reuse reporting ("distinguish contributions to owned versus non-owned
Packages") joined with a Data-Product ownership view (AD-15's "derived... ownership maps"), which
is explicitly Herald's remit per AD-17 ("reporting and the outward communication surface") — the
join fails: there is no canonical mapping from `priya@company.com` to `team-customer-eng` (or
vice versa) anywhere the spine specifies, so "who owns X" cannot be answered uniformly across
planes, only per-plane.

**Proposed AD (new):**
> **AD-22 — One identity shape for every ownership field.** **Binds:** FR-5, FR-33, FR-38, FR-51,
> AD-15, AD-17. **Prevents:** an ownership join across planes silently failing because two planes
> independently chose incompatible identity representations for "owner." **Rule:** every `owner`,
> `Trusted Committer`, and Mandate-override-decision field across every Package, Asset, and
> decision record uses one platform-declared identity representation (a Domain-scoped team
> identifier, resolvable to individuals through one directory). A field declaring an owner in any
> other shape fails the Quality Gate.

---

### Hole 7 — Nothing stops a second Domain re-publishing another Domain's entity as its own (AD-7, AD-15, § 10 Non-Goals)

**Units:** the `customer` domain's `customer_curated_customer_profile_publish` Asset (Curated
layer, publishes identity/profile fields for the `customer` entity, contract v1) and the `cdo`
domain's `cdo_consumption_customer_360_publish` Asset (Consumption layer, ingests
`customer`'s published product, then republishes its own enriched "customer 360" view that
includes copies of the identity/profile fields as `cdo`-owned fields, versioned on `cdo`'s own
cadence).

**Letter-compliance:** `cdo` consumed `customer`'s data exclusively through the **published**
Data Product, never touching `customer`'s datastore directly (AD-7's literal rule: "A Domain may
consume another Domain's published Data Product... it may never import another Domain's Package
or reach its datastore directly" — satisfied). `cdo`'s new Asset has its own owner, Domain,
Layer, update frequency, valid name, and versioned contract (AD-15/AD-16 — satisfied). No AD
prohibits a Domain from including another Domain's fields, by value, in its own published
contract once lawfully consumed.

**Incompatibility:** there are now two Domains each publishing an authoritative-looking "customer
profile" shape — `customer`'s original and `cdo`'s enriched copy — under different names,
different schemas, and different versioning cadences. A third Domain consuming "customer profile
data" has no way to know which is canonical; if `customer` fixes a data-quality defect in its
Curated layer, `cdo`'s republished copy silently continues to carry the stale value until its own
next refresh, with no contract linking the two as the same fact. This is precisely what § 10's
Non-Goal forbids in spirit ("Unity does not maintain a second registry of truth... anything else
is derived") without violating AD-7 or AD-15's letter, because both ADs govern *access path*
(consume via the published product) and *metadata structure* (declare owner/Domain/Layer/
contract), not *field-level provenance* (may a consumer restate a producer's fields as its own?).

**Proposed AD (new):**
> **AD-23 — An entity has one Domain of record per Layer; downstream Domains reference, they do
> not restate.** **Binds:** AD-7, AD-15, AD-16, § 10 Non-Goals. **Prevents:** a second Domain
> republishing another Domain's owned fields as its own, reintroducing the second-registry-of-
> truth failure through a lawful consumption path. **Rule:** a derived registry (per AD-15) maps
> each entity to its owning Domain per Layer. A Data Product that includes another Domain's owned
> fields must express them as a versioned reference to the source contract (join-at-query or
> pass-through with source-contract-version lineage recorded), never as a copied, independently-
> versioned restatement. A new Data Product whose declared entity already has an owning Domain at
> that Layer fails the gate unless it is that Domain, or its contract records the source reference
> instead of duplicating the fields.

---

## 2. AD overlap / potential-contradiction findings (non-blocking, but worth resolving)

- **AD-4 × AD-13 × AD-20 (see Hole 2).** AD-4 decouples Stage count from Environment count; AD-20
  attaches a behavioral requirement to the Stage; AD-13 says the Environment inherits nothing
  implicit. None of the three states which layer materializes AD-20's requirement when Stages
  share an Environment — read together they're merely silent, not contradictory, but the silence
  is exactly where Hole 2 lives. Closing it with AD-21 above removes the ambiguity.
- **AD-9 × AD-6.** AD-6 requires the compliance capability be "invoked as a command," never
  "invoked only in CI." AD-9 requires every check be a named task with CI-vs-local parity. These
  are mutually reinforcing, not contradictory — flagged only because a shallow read of "never
  invoked only in CI" could be mistaken for a stronger claim (e.g., that it must run outside the
  task mechanism); worth one clarifying sentence in AD-6 that the compliance command is itself
  wrapped as an AD-9 task like any other check.
- **AD-13's "isolated-tool Environment" vs FR-7's compatibility-detection Environment.** FR-7's
  Environment deliberately composes the *full* mandated stack — the opposite of "minimal." AD-13's
  Prevents clause is scoped to Environments "declared minimal-footprint," and FR-7 explicitly
  states its Environment is "not a deployable Environment," so the two don't actually conflict —
  but AD-13's binding list ("every deployable Environment (and every isolated-tool Environment)")
  doesn't make FR-7's exclusion explicit at the AD level, only at the FR level. A reader of AD-13
  alone could flag FR-7's Environment as a violation. Suggest AD-13 cross-reference FR-7 the way
  AD-4 cross-references FR-9.

## 3. Rules with no stated enforcement point, or aspirational as written

- **AD-18 ("Failures name their cause").** The Rule enumerates what a failure must name (unmet
  requirement, conflicting constraint and the two packages that hold it, violated Mandate
  identifier, uncovered platform) but names no check that verifies a failure message actually
  satisfies this — unlike AD-10 (an explicit scan), AD-14 (an explicit duplication check), or AD-9
  (an explicit parity check). For third-party-tool-sourced failures (a raw solver error from the
  workspace manager, for instance) "the two packages that hold [the conflict]" may not always be
  extractable without wrapping every tool's error output — the Rule reads as a design intent more
  than an enforceable gate as currently scoped. Recommend either naming the enforcement mechanism
  (a message-shape linter over gate output) or acknowledging the residual "opaque third-party
  error" case explicitly, the way AD-20 explicitly scopes content inspection out.
- **AD-19 ("no environment hostname, endpoint, or credential is hardcoded in code").** AD-10 has
  an explicit sibling clause elsewhere in the PRD ("A scan for credential-bearing URL patterns
  fails the Quality Gate," FR-15) for the credential half. The hostname/endpoint half of AD-19 has
  no equivalent stated scan anywhere in the spine or the Capability → Architecture Map — it's
  asserted as a Rule with the enforcement point left implicit. Worth either pointing at the same
  scan mechanism explicitly or flagging it as a distinct, currently-unassigned check.

---

## Verdict rationale

**changes-requested.** The spine's ADs are individually well-formed and each closes a real,
evidenced defect from the intake set — but seven concrete pairs of units, each fully compliant
with every AD to the letter, still build incompatibly: two contract shapes, one Stage-control
mutation path left unassigned, two derived artifacts pinned to different points in time, one task
name with two meanings, one capability with two owners, one ownership field with two shapes, and
one entity with two publishers. All seven are closeable with the tightened/new AD language
proposed above (AD-21, AD-22, AD-23, plus targeted amendments to AD-2, AD-9, AD-16, AD-17) without
changing the spine's altitude or paradigm. Recommend folding these into the spine before it's used
to gate feature-level (one-level-down) design work, since every hole above is exactly the seam
where two independently-built features would silently diverge.
