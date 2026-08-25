# PyForge fleet drain — status snapshot

**Updated:** 2026-08-25 13:50 CDT
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md) · [SEQUENCING.md](./SEQUENCING.md)

## Coordinator lock (singleton)

| Field | Value |
|-------|--------|
| `owner` | parent-chat (this Cursor session — **the only orchestrator**) |
| `held_since` | 2026-08-24T21:20-05:00 |
| `state` | complete (drain queues **0**; steward 12-7 `/ht/` 200) |

**HARD:** Do **not** launch a background coordinator Task, `marshal drain`, or a second parent chat that dispatches. Hourly `fleet-picture` is a **report loop only** — it must not dispatch stories. Dispatch agents (e.g. steward 18-1) are workers, not coordinators.

Canopy tranche reopen. Previous campaign was complete except steward `12-7`. New backlog is steward Epics 18–32 + peer CAP-18 process stories.

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` (skip-listed keys only remain at exit) |
| Sequence | Wave 0 `18-1` → Wave 1 `32-1` → Wave 2 seven peers + steward `18-2` |
| Skips | none (12-7 unblocked: CRC Running + `crc start -p` complete) |

## Merge policy

If GitHub Actions billing still blocks CI: **local tests green → `gh pr merge <n> --merge --admin`** (never squash). Prefer required checks when they run.

## Hourly report

Stopped (loop PID `3794219` terminated). Report-only; do not restart unless the operator asks.

## In-flight

None. Steward `12-7` **done** (CRC `/ht/` 200, Liquibase + migrate Complete, ledger synced).

## Blocked

None.

## Operator skip

None. Campaign drain queues **0**.

## Recently merged (Wave 2)

| Station | Story | Evidence |
|---------|--------|----------|
| mason | `10-1` | [#734](https://github.com/rxm7706/local-recipes/pull/734) — **mason DRAINED** |
| scribe | `4-1` | [#735](https://github.com/rxm7706/local-recipes/pull/735) `5b16a956da` · ledger [#737](https://github.com/rxm7706/local-recipes/pull/737) `7c968cae45` — **scribe DRAINED** |
| herald | `16-1` | [#733](https://github.com/rxm7706/local-recipes/pull/733) `8669ec8d8d` · ledger [#736](https://github.com/rxm7706/local-recipes/pull/736) `d3fa7abc99` — **herald DRAINED** |
| atlas | `18-1` | [#738](https://github.com/rxm7706/local-recipes/pull/738) `be05c7beaa` · ledger [#740](https://github.com/rxm7706/local-recipes/pull/740) `1223609b45` — **atlas DRAINED** |
| marshal | `26-1` | [#739](https://github.com/rxm7706/local-recipes/pull/739) `b225c9f5c7` · ledger `18921e1341` — **marshal DRAINED** |
| steward | `18-2` | [#741](https://github.com/rxm7706/local-recipes/pull/741) `7d9518d1ed` · ledger `9174d97fd4` |
| warden | `9-1` | [#742](https://github.com/rxm7706/local-recipes/pull/742) `e374e43102` · ledger [#744](https://github.com/rxm7706/local-recipes/pull/744) `f55f8e116f` |
| doctor | `17-1` | [#743](https://github.com/rxm7706/local-recipes/pull/743) `037097adc2` · ledger [#745](https://github.com/rxm7706/local-recipes/pull/745) `4a07ba8fca` — **doctor DRAINED** |
| steward | `18-3` | [#746](https://github.com/rxm7706/local-recipes/pull/746) `15b1202a6b` · ledger [#747](https://github.com/rxm7706/local-recipes/pull/747) `a4738f942f` |
| warden | `9-2` | [#748](https://github.com/rxm7706/local-recipes/pull/748) `cb89cd3f5d` · ledger [#749](https://github.com/rxm7706/local-recipes/pull/749) `bf025506f4` |
| steward | `19-1` | [#750](https://github.com/rxm7706/local-recipes/pull/750) `0c24680b3b` · ledger [#751](https://github.com/rxm7706/local-recipes/pull/751) `61b8874fa8` |
| warden | `9-3` | [#752](https://github.com/rxm7706/local-recipes/pull/752) `4d7bf8cff6` · ledger [#753](https://github.com/rxm7706/local-recipes/pull/753) `425f1295f3` — **warden DRAINED** |
| steward | `19-2` | [#754](https://github.com/rxm7706/local-recipes/pull/754) `7e5fe82168` · ledger [#755](https://github.com/rxm7706/local-recipes/pull/755) `d8f0a702bf` |
| steward | `20-1` | [#756](https://github.com/rxm7706/local-recipes/pull/756) `12264c5628` · ledger [#757](https://github.com/rxm7706/local-recipes/pull/757) `7deee8965e` · queues [#758](https://github.com/rxm7706/local-recipes/pull/758) `4d816a6dbc` |
| steward | `20-2` | [#759](https://github.com/rxm7706/local-recipes/pull/759) `5c6764d9f5` · ledger [#760](https://github.com/rxm7706/local-recipes/pull/760) `4dc8d8abda` |
| steward | `21-1` | [#761](https://github.com/rxm7706/local-recipes/pull/761) `3f741613ec` · ledger [#762](https://github.com/rxm7706/local-recipes/pull/762) `844a4ff461` |
| steward | `21-2` | [#763](https://github.com/rxm7706/local-recipes/pull/763) `716a8d236e` · ledger [#764](https://github.com/rxm7706/local-recipes/pull/764) `24f670472b` |
| steward | `21-3` | [#765](https://github.com/rxm7706/local-recipes/pull/765) `836478d90d` · ledger [#766](https://github.com/rxm7706/local-recipes/pull/766) `4b88f3f124` |
| steward | `21-4` | [#767](https://github.com/rxm7706/local-recipes/pull/767) `ff6b71391b` · ledger [#768](https://github.com/rxm7706/local-recipes/pull/768) `e52e620351` |
| steward | `21-5` | [#769](https://github.com/rxm7706/local-recipes/pull/769) `1cb4b1604d` · ledger [#770](https://github.com/rxm7706/local-recipes/pull/770) `8c97d5baec` |
| steward | `22-1` | [#771](https://github.com/rxm7706/local-recipes/pull/771) `609ce3facc` · ledger `541f9b0404` |
| steward | `23-1` | [#772](https://github.com/rxm7706/local-recipes/pull/772) `3ba9ed3204` · ledger [#773](https://github.com/rxm7706/local-recipes/pull/773) `152a0f3cc1` |
| steward | `24-1` | [#774](https://github.com/rxm7706/local-recipes/pull/774) `43ad76835e` · ledger [#775](https://github.com/rxm7706/local-recipes/pull/775) `473f45722c` |
| steward | `24-2` | [#777](https://github.com/rxm7706/local-recipes/pull/777) `fe00cf3aba` · ledger [#778](https://github.com/rxm7706/local-recipes/pull/778) `2b8d4a33b6` |
| steward | `25-1` | [#779](https://github.com/rxm7706/local-recipes/pull/779) `817f8ddd81` · ledger [#780](https://github.com/rxm7706/local-recipes/pull/780) `9d6df2e39f` |
| steward | `25-2` | [#781](https://github.com/rxm7706/local-recipes/pull/781) `0c49fa2eed` · ledger [#782](https://github.com/rxm7706/local-recipes/pull/782) `a76381bf8f` |
| steward | `25-3` | [#783](https://github.com/rxm7706/local-recipes/pull/783) `06dbadd503` · ledger [#784](https://github.com/rxm7706/local-recipes/pull/784) `cc235ef3aa` |
| steward | `25-4` | [#785](https://github.com/rxm7706/local-recipes/pull/785) `c285b0675e` · ledger [#786](https://github.com/rxm7706/local-recipes/pull/786) `cef7f261f6` |
| steward | `26-1` | [#787](https://github.com/rxm7706/local-recipes/pull/787) `0d7a116477` · ledger [#788](https://github.com/rxm7706/local-recipes/pull/788) `f3507a79d6` |
| steward | `26-2` | [#789](https://github.com/rxm7706/local-recipes/pull/789) `67a6c05ead` · ledger [#790](https://github.com/rxm7706/local-recipes/pull/790) `f68b595b31` |
| steward | `28-1` | [#791](https://github.com/rxm7706/local-recipes/pull/791) `79d57b04ac` · ledger [#792](https://github.com/rxm7706/local-recipes/pull/792) `544fc54980` |
| steward | `28-2` | [#793](https://github.com/rxm7706/local-recipes/pull/793) `bbdd6b68fe` · ledger [#794](https://github.com/rxm7706/local-recipes/pull/794) `a5e9dad59a` |
| steward | `29-1` | [#795](https://github.com/rxm7706/local-recipes/pull/795) `3069aed1ea` · ledger [#796](https://github.com/rxm7706/local-recipes/pull/796) `ddafd7c6d8` |
| steward | `29-2` | [#797](https://github.com/rxm7706/local-recipes/pull/797) `7193d7bf55` · ledger [#798](https://github.com/rxm7706/local-recipes/pull/798) `0f1ebeb94b` |
| steward | `29-3` | [#799](https://github.com/rxm7706/local-recipes/pull/799) `dc45242b30` · ledger [#800](https://github.com/rxm7706/local-recipes/pull/800) `00eac79614` |
| steward | `30-1` | [#801](https://github.com/rxm7706/local-recipes/pull/801) `0eaccad333` · ledger [#802](https://github.com/rxm7706/local-recipes/pull/802) `f5f0bccf3b` |
| steward | `30-2` | [#803](https://github.com/rxm7706/local-recipes/pull/803) `c3ac2f3ec2` · ledger [#804](https://github.com/rxm7706/local-recipes/pull/804) `a3784c33ed` |
| steward | `31-1` | [#805](https://github.com/rxm7706/local-recipes/pull/805) `97dc86e81e` · ledger [#806](https://github.com/rxm7706/local-recipes/pull/806) `5991574f8b` |
| steward | `31-2` | [#807](https://github.com/rxm7706/local-recipes/pull/807) `e5b12bf8c6` · ledger [#808](https://github.com/rxm7706/local-recipes/pull/808) `5bbfc37527` |
| steward | `31-3` | [#809](https://github.com/rxm7706/local-recipes/pull/809) `047bfa9cfe` · ledger [#810](https://github.com/rxm7706/local-recipes/pull/810) `ce01ee04d6` |
| steward | `32-2` | [#811](https://github.com/rxm7706/local-recipes/pull/811) `127d380bfe` · ledger [#812](https://github.com/rxm7706/local-recipes/pull/812) `62db654dd3` |

## Next after 12-7 (queued 2026-08-25)

Fold the Containerfile pip layer into a single `pixi install -e python-agent-platform` (PyPI extras on that feature, lock-time overlap, no `pip install --no-deps`). **Pixitainer** is in scope as a *re-eval of the Docker backend*, not as a drop-in for today’s pip `RUN`. **Specified 2026-08-25:** [Dream](../../docs/dreams/platform-image-one-pixi-env.md) + [SPEC](../../_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-platform-image-one-pixi-env/SPEC.md) (`ready`). Queue note: [NEXT-AFTER-12-7.md](./NEXT-AFTER-12-7.md). Do not implement until that spec is the build input.

Q5 measures parked: `docs/dreams/build-league-scorecard.md` (draft spec, unpublished metrics). `lane1-serves-dw-h3` answered **no**.

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
```
