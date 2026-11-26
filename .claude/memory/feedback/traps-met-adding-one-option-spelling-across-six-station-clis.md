---
name: "traps-met-adding-one-option-spelling-across-six-station-clis"
description: "Traps met adding one option spelling across six station CLIs (2026-11-26, branch json-output-2026-11-26, PR #2398; stew…"
metadata:
  type: feedback
---

Traps met adding one option spelling across six station CLIs (2026-11-26, branch json-output-2026-11-26, PR #2398; steward 144.1/145.1 and five relays): (1) Adding an argparse option beside an existing one can make a prefix that used to resolve ambiguous (--js, --form); register an added twin so it matches only in full (pyforge.core.cli_output wraps _get_option_tuples), and check abbreviations before and after. (2) A coverage gate red only under pr-preflight can be the preflight's suite reduction, not the code: mason's gate read 34% because the reduced lane ran part of the suite while the gate judged the whole report; steward 145.1 now runs a suite whole when its gate passes --report. (3) A new public name in pyforge-core must join the kernel contract's Public names list (spec-pyforge-core contract.md) or the core contract test reds. (4) The repo-root scripts lane runs in pyforge-guild, which does not install atlas or warden: a test there that importorskips a station's module skips silently, so hold that station's case in its own suite. (5) Every SPEC.md render is denied by the auto-mode classifier until the operator approves it in session: write the memlog decision, prepare an anchor-asserting render with a --check mode, and ask once for every Spec the change renders.
