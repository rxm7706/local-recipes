# Air-gap distribution contract (mason Story 9.2)

This is the **socket**, not an installer. Any external distributable
(Miniforge/constructor, vendor mirror, enterprise offline bundle) must
satisfy the contract below, then register through mason's empty backend
registry (`pyforge.mason.airgap_contract.SUPPORTED_DISTRIBUTABLES`).

Coordinated with steward Story 12.3's air-gap parity run — that story
**consumes** this contract; it does not redefine it.

## Required capabilities

| Key | Meaning |
|-----|---------|
| `mirrored_channel_set` | Pinned conda/pixi channels the offline tree mirrors |
| `pixi_bootstrap_path` | Path from a bare machine to a working pixi that resolves this repo offline |
| `verification_hooks` | Post-install checks proving the mirror is usable |

Machine-readable twin: `AIRGAP_CONTRACT` in
`src/shared/packages/pyforge-mason/src/pyforge/mason/airgap_contract.py`.

## Registry

`SUPPORTED_DISTRIBUTABLES` starts **empty**. A backend registers via
`register_distributable(DistributableBackend(...))` after
`validate_backend_shape` accepts it. One entry at a time — same discipline
as steward `_SUPPORTED_MODULES`.

## Non-goals

Building a Miniforge/constructor installer in this repo. The 63-family CI
architecture. Changing steward 12.3's implementation beyond consuming this
contract.
