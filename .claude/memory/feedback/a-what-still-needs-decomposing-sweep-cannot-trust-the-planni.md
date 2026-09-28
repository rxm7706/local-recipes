---
name: "a-what-still-needs-decomposing-sweep-cannot-trust-the-planni"
description: "A 'what still needs decomposing' sweep cannot trust the planning detectors alone: chain-completeness, dream-chain and c…"
metadata:
  type: feedback
---

A 'what still needs decomposing' sweep cannot trust the planning detectors alone: chain-completeness, dream-chain and chain-currency were all green on 2026-09-27 while four undecomposed seeds sat inside station Dreams (new work enters as a dated 'Proposed:' or '(seed)' entry appended to docs/dreams/pyforge-<station>.md, and nothing links an entry to a CAP). Also grep docs/dreams/*.md for 'not yet specced', 'No CAP minted', 'Status: **seed' and 'next bmad-spec pass', check each Proposed entry for a '-> CAP-n / Story n.m' pointer, and check team memory for operator directions not yet in a Dream. For dispatchability, use marshal's own functions (spec_binding.parse_success_signal plus gate.check_spec_binding against the station's composed verify_commands, spec_deps.ready_backlog, dispatch_fleet.station_backlog and plan_station_queue with fleet-drain-queue.yaml) until 'marshal factory drain --plan' (marshal Story 65.1) exists; prose like 'Parked ... do not dispatch' is read by no code, so park with skip_policies.
