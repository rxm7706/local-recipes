# Analysis — cluster requires mcp-host (CAP-4)

**Date:** 2026-08-26  
**SPEC:** `spec-mcp-era-isolation`  
**Story:** Epic 35 / `35-1-cluster-requires-mcp-host`  
**Not:** Epic 34 / CAP-19. **Not:** slice 3 (`retire-skip.md`).

## What the operator asked

The mcp-host **bridge** already isolates mcp 1.x (web + Langflow) from mcp 2.x
(sidecar). Enforce that isolation **on the cluster** now: the overlay cannot
ship without the sidecar and the proxy URL. Do not treat host MCP as an
optional leftover of Epic 34.

## What slice 1 already shipped (do not rebuild)

| Surface | Fact (2026-08-26) |
|---|---|
| Pixi | `[feature.mcp-host]` solves mcp 2.x; no FastMCP 3. `python-agent-platform` stays mcp 1.28.x. |
| Code | `django_pyforge.mcp_http.dispatch_station_mcp` proxies when `MCP_HOST_SIDECAR_BASE_URL` is set. Unreachable sidecar → HTTP 502 + error log. URL unset → in-process face or ImportError skip. |
| Chart | `templates/mcp-host-deployment.yaml` + Service always render. **No** `mcpHost.enabled`. `values.yaml` `mcpHost.image.repository: platform-mcp-host`. |
| Tests | `test_mcp_host_deployment_and_service_restricted_v2`, `test_platform_pods_wire_mcp_host_sidecar_base_url_to_internal_service` (helm template). `test_mcp_host_sidecar.py` (proxy + dual-era). |
| CRC memlog | Slice 1 proofs: `/ht/` 200; initialize echo; header 2026-07-28; `-32022`; GET 405. Overlay image `crc-20260826c`. |

The bridge **works**. What is not fail-loud is **omission**.

## Gaps (this story)

1. **Helm `required`.** Templates assume `mcpHost.image`. Empty `repository` can
   still template a broken image ref. CAP-4: `helm template` **fails** if
   `mcpHost.image.repository` is empty. Do **not** add `mcpHost.enabled`.
2. **Django cluster check.** No `django.core.checks` require the URL under
   production/cluster settings. Laptop must still boot with the URL unset.
3. **Bring-up docs.** `cluster-bringup.md` does not name mcp-host as a required
   workload next to web / worker / dbgpt-sidecar.
4. **OCP overlay.** `deploy/overlays/ocp/` has no `mcpHost` stanza — it inherits
   chart defaults. That is correct if defaults stay required; document it so an
   overlay cannot blank the image.

## What must stay optional / parked

| Item | Why |
|---|---|
| ImportError skip | Laptop + mcp 1.x gunicorn. Slice 3 only when FastMCP 4 is on conda-forge **or** Langflow drops `mcp<2`. |
| Lift mcp 2 on `python-agent-platform` | Unsolvable with FastMCP 3 / Langflow. |
| Web CrashLoop if sidecar down | Langflow must stay up. 502 on MCP path only. |
| Query plane / ATTACH | Epic 34. Different leftover. |
| Factory stdio translator | Slice 2. Own problem. |

## Dispatch

`bmad-build` + `spec-35-1-cluster-requires-mcp-host.md` **after** 34.1 (no
code dep; keep sessions serial). `BMAD_ACTIVE_PROJECT=pyforge-steward`.
Physical paths only. Never `bmad-switch`.
