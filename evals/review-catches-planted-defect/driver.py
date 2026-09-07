#!/usr/bin/env python3
"""Twin-run driver for spec-45-2 (Story 45.2): measures whether the edge-case-hunter
review layer catches a planted boundary-flip defect. Subprocess-only for the LLM call
-- shells out to the installed ``claude`` CLI, never imports it as a library. Reading
local config files (marshal-policy.toml, the rendered harness policy) is fine; only how
the LLM call happens is subprocess-only.

Usage:
  driver.py smoke
  driver.py twin-run [--trials N] [--model MODEL] [--max-budget-usd USD] [--out-dir DIR]
  driver.py replay <sealed-record-path>
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
PLANTED = "pkg/discount.py:17"
SENTINEL = {"location": "__no-findings__", "trigger_condition": "sentinel: no findings reported",
            "guard_snippet": "", "potential_consequence": ""}
LOC_RE = re.compile(r"^(.*):(\d+)(?:-(\d+))?$")
ARMS = {"clean": {"probe_id": "P-001", "diff": "clean.diff", "defect_present": False},
        "mutated": {"probe_id": "P-002", "diff": "mutated.diff", "defect_present": True}}
PROJECT_POLICY = REPO_ROOT / "_bmad-output/projects/pyforge-steward/planning-artifacts/marshal-policy.toml"
# Last-resort literal, used only if BOTH the project policy AND a live `marshal config`
# call are unavailable (e.g. pyforge-marshal itself cannot run). Documented here rather
# than silently guessed: as of this story, Marshal's own built-in `[adapter.review].model`
# baseline is "opus" (see pyforge-marshal's `_POLICY_TEMPLATE` /
# `ADAPTER_REVIEW_MODEL_STOCK_DEFAULT`, re-verified live via
# `pixi run -e pyforge-marshal marshal config --project pyforge-steward
# --write-harness-policy <dir>` on 2026-09-06) -- NOT "fable"; that value predates the
# 2026-08-02 repo-wide raise and is stale everywhere else it is still quoted.
LAST_RESORT_MODEL = "opus"


def run(cmd, **kw):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, **kw)
    except FileNotFoundError as exc:
        sys.exit(f"driver: could not find executable {exc.filename!r} on PATH "
                 f"(command was: {' '.join(str(c) for c in cmd)})")


def resolve_model(cli_override):
    """[adapter.review].model, via Marshal's real resolution chain (never a bare
    literal with no documented fallback path): (1) an explicit --model flag; (2) this
    project's marshal-policy.toml, parsed with stdlib tomllib, if it declares
    [adapter.review].model; (3) `marshal config --write-harness-policy` -- the Code
    Map's own escape hatch for "a marshal command that already resolves it" -- rendered
    to a throwaway directory and read back; (4) LAST_RESORT_MODEL, only if marshal
    itself could not run."""
    if cli_override:
        return cli_override
    if PROJECT_POLICY.exists():
        try:
            doc = tomllib.loads(PROJECT_POLICY.read_text())
            model = doc.get("adapter", {}).get("review", {}).get("model")
            if model:
                return model
        except (tomllib.TOMLDecodeError, OSError, AttributeError, UnicodeDecodeError):
            pass
    with tempfile.TemporaryDirectory() as td:
        r = run(["pixi", "run", "-e", "pyforge-marshal", "marshal", "config",
                 "--project", "pyforge-steward", "--write-harness-policy", td], cwd=REPO_ROOT)
        rendered = Path(td) / ".bmad-loop" / "policy.toml"
        if r.returncode == 0 and rendered.exists():
            try:
                doc = tomllib.loads(rendered.read_text())
                model = doc.get("adapter", {}).get("review", {}).get("model")
                if model:
                    return model
            except (tomllib.TOMLDecodeError, OSError, AttributeError, UnicodeDecodeError):
                pass
    return LAST_RESORT_MODEL


def eq(*args, out=None):
    cmd = ["pixi", "run", "-e", "local-recipes", "eval-quality", *args]
    if out is not None:
        cmd += ["--out", str(out)]
    r = run(cmd, cwd=REPO_ROOT)
    return r.returncode, r.stdout, r.stderr


def eval_quality_prefix():
    """The conda prefix `eval-quality` is installed under, resolved through the
    local-recipes pixi env rather than a hardcoded `.pixi/envs/...` path (portable
    across a differently-configured pixi envs dir)."""
    r = run(["pixi", "run", "-e", "local-recipes", "bash", "-lc", "command -v eval-quality"], cwd=REPO_ROOT)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    bin_path = Path(r.stdout.strip().splitlines()[-1])
    return bin_path.parent.parent


def canonical_digest(obj):
    canon = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()


def byte_digest(path):
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cites_planted(raw_findings):
    """Exact file:line match only, per contract.json's own oracle commentary
    ("Resolves caught/missed by exact file:line match against the one planted defect
    location"). Deliberately NOT a range-overlap check: confirmed empirically that an
    unrelated finding spanning a wider range that merely overlaps line 17 (e.g. a
    NaN/infinity concern reported as "pkg/discount.py:15-17") is not a citation of the
    boundary-flip defect, and counting it as one produced a false positive on the
    clean arm. A degenerate single-line range ("17-17") still counts; a genuine
    multi-line range does not."""
    for f in raw_findings:
        if not isinstance(f, dict):
            continue
        m = LOC_RE.match(str(f.get("location", "")).strip())
        if not m:
            continue
        file_part = m.group(1).strip()
        start = int(m.group(2))
        end = int(m.group(3)) if m.group(3) else start
        if f"{file_part}:{start}" == PLANTED and start == end:
            return True
    return False


def invoke_review(diff_path, model, budget_usd):
    """Runs the edge-case-hunter layer headlessly via `claude -p`. Returns
    (raw_findings, stdout_text, exit_code, cost_usd, wall_seconds). Never raises: a
    non-zero claude exit or an unparseable response yields an empty findings list, per
    the I/O matrix -- the driver records a FAIL observation, it never crashes.

    The prompt file is passed verbatim via --system-prompt and the diff is inlined
    directly into the user message (per edge-case-hunter.md's own "CONTENT SOURCE"
    section: "Review content:" gives the content itself or a path to read it from) --
    deliberately NOT a path the model would need a Read tool call to resolve, since
    isolation-manifest.json declares toolInventory/toolAllowlist empty: this reviewer
    call uses no tools at all, so nothing needs to be permitted.

    fixture-intent.md (the fixture's own Intent + Tasks & Acceptance -- the "spec this
    change was built from" edge-case-hunter.md's Step 5 claims_file names) is inlined
    after the diff, clearly labelled for Step 5 only. Confirmed empirically: without it,
    the boundary check's own inclusive-vs-exclusive ambiguity reads as a plausible
    finding on the CLEAN arm too (the model cannot tell the `>=` is deliberate), a false
    positive Step 5's claims check exists precisely to rule out once it can compare the
    code against the documented intent."""
    system_prompt = (HERE.parents[1] / ".claude/skills/bmad-build-auto/review-prompts/edge-case-hunter.md").read_text()
    diff_text = Path(diff_path).read_text()
    claims_text = (HERE / "fixture-intent.md").read_text()
    prompt = (
        f"Review content:\n\n{diff_text}\n\n"
        "claims_file (do not consult this until your instructions' Step 5 -- it is the "
        f"spec this change was built from):\n\n{claims_text}"
    )
    schema = (HERE / "findings-schema.json").read_text()
    cmd = ["claude", "-p", prompt, "--system-prompt", system_prompt,
           "--output-format", "json", "--json-schema", schema,
           "--max-budget-usd", str(budget_usd), "--no-session-persistence", "--model", model,
           "--disallowedTools", "Bash,Read,Write,Edit,WebFetch,WebSearch,Task,Glob,Grep"]
    t0 = time.monotonic()
    # 630s = the isolation manifest's own maxWallClockMinutes: 10 ceiling plus a small
    # buffer, so a hung claude -p process cannot hang this pixi task indefinitely.
    try:
        r = run(cmd, cwd=REPO_ROOT, timeout=630)
    except subprocess.TimeoutExpired as exc:
        wall = time.monotonic() - t0
        partial = (exc.stdout or "") + (exc.stderr or "")
        return [], f"driver: claude -p timed out after {exc.timeout}s\n{partial}", 124, 0.0, wall
    wall = time.monotonic() - t0
    if r.returncode != 0:
        return [], r.stdout + r.stderr, r.returncode, 0.0, wall
    raw, cost, parse_ok = parse_review_envelope(r.stdout)
    if not parse_ok:
        # A malformed/unexpected-shape envelope is infrastructure breakage, not a
        # genuine empty-findings review -- must not be scored identically to success.
        return [], r.stdout, 1, cost, wall
    return raw, r.stdout, 0, cost, wall


def parse_review_envelope(stdout_text):
    """Pulls (findings, cost) out of one `claude -p --output-format json` envelope.
    Returns (findings, cost_usd, parse_ok) -- parse_ok is False for a malformed or
    unexpected-shape envelope, distinguishing that case from a well-formed envelope
    that genuinely reports zero findings (both would otherwise collapse to the same
    empty findings list)."""
    try:
        envelope = json.loads(stdout_text)
        structured = envelope.get("structured_output")
        cost = float(envelope.get("total_cost_usd", 0.0))
        if not isinstance(structured, dict):
            result_text = envelope.get("result", "{}")
            structured = json.loads(result_text) if isinstance(result_text, str) else result_text
        if not isinstance(structured, dict):
            return [], cost, False
        raw = structured.get("findings", [])
        if not isinstance(raw, list):
            return [], cost, False
        return raw, cost, True
    except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
        return [], 0.0, False


def runtime_evaluator_configuration(model):
    """Loads the static evaluator-configuration.json template and overrides the two
    fields that must reflect THIS run rather than a stale file value: modelSnapshot
    (spec Task 77: "model placeholder resolved at run time by the driver, not
    hardcoded in this file") and systemPromptDigest (the real digest of the prompt
    file actually sent, not a copy-pasted placeholder)."""
    cfg = json.loads((HERE / "evaluator-configuration.json").read_text())
    cfg["modelSnapshot"] = model
    cfg["systemPromptDigest"] = byte_digest(REPO_ROOT / ".claude/skills/bmad-build-auto/review-prompts/edge-case-hunter.md")
    return cfg


def build_record(run_id, arm, probe_id, trial, raw_findings, defect_present, digests, stdout_text,
                  exit_code, cost_usd, wall_seconds, isolation_ref, actions_ref):
    body_findings = raw_findings if raw_findings else [SENTINEL]
    hit = cites_planted(raw_findings)
    truncated = len(stdout_text) > 4000
    findings = []
    if hit:
        findings.append({
            "findingType": "defect", "findingId": "F-001", "oracleId": "O-001",
            "probeId": probe_id, "behaviorId": "B-001", "severity": "critical",
            "summary": f"The review cited {PLANTED}, the planted boundary-flip line.",
            "confidence": 0.9, "observationIds": ["review-obs-1"], "evidenceArtifacts": [],
            "quotedEvidence": [{"quote": PLANTED, "channel": "response-body"}],
        })
    return {
        "schemaVersion": 1, "parentDigest": None, "revisionCount": 0, "runId": run_id,
        "conditionArm": arm, "mode": "contract-scoring", "trialIndex": trial,
        "contractDigest": digests["contract"], "sealedBriefDigest": digests["brief"],
        "evaluatorConfigurationDigest": digests["evaluator_config"],
        "evaluatorRecommendation": "FAIL" if hit else "PASS",
        "oracleDispositions": [{"oracleId": "O-001", "disposition": "violated" if hit else "held",
                                 "observationIds": ["review-obs-1"], "note": None}],
        "findings": findings,
        "observations": [{
            "observationId": "review-obs-1", "sequence": 1, "operationId": "review-diff",
            "provenance": "evaluator-chosen",
            "callInputs": {"path": None, "query": None, "header": None, "body": None},
            "responseBody": {"ok": exit_code == 0, "findings": body_findings,
                              "defectPresent": defect_present},
            "responseHeaders": None, "responseStatus": 200 if exit_code == 0 else None,
            "stdout": stdout_text[:4000], "stderr": None, "exitCode": exit_code,
        }],
        "judgeResults": [], "actionsArtifact": actions_ref, "isolationManifestArtifact": isolation_ref,
        "resourceUse": {"toolCalls": 0, "inputTokens": 0, "outputTokens": 0,
                         "wallClockSeconds": wall_seconds, "costUsd": str(cost_usd)},
        "evidenceDisclosure": {"truncationBound": 4000 if truncated else None,
                                "reportedIncomplete": truncated},
        "invalidReason": None,
    }, hit


def control_leg(probe_id, defect_present):
    """A ProbeObservation leg for `eval-quality preflight`'s --observations input:
    echoes one of the plan's synthetic leg ids back as probeId (README: "each
    observation echoes a planned leg's id back as probeId"), carrying a JSON body
    shaped like the contract's own review-diff response."""
    return {"probeId": probe_id, "interfaceId": "review-api", "operationId": "review-diff",
            "status": 200, "headers": {},
            "body": {"kind": "json", "value": {"ok": True, "findings": [SENTINEL],
                                                "defectPresent": defect_present}}}


def prepare_shared(out_dir, model, budget):
    """Compiles/seals the contract once, builds this run's evaluator-configuration
    (model + system-prompt digest resolved), and preflights both arms once. Returns
    (digests, corpus_digest, isolation_refs, actions_ref, preflight_paths, eval_contract,
    evalcfg_path)."""
    contract = HERE / "contract.json"
    eval_contract = out_dir / "eval-contract.json"
    brief = out_dir / "sealed-evaluator-brief.json"
    for args, out in ((["compile", "--in", str(contract)], eval_contract),
                       (["seal", "--in", str(contract)], brief)):
        code, _, err = eq(*args, out=out)
        if code != 0:
            sys.exit(f"driver: {' '.join(args)} failed (exit {code}): {err.strip()}")

    evalcfg = runtime_evaluator_configuration(model)
    evalcfg_path = out_dir / "evaluator-configuration.json"
    evalcfg_path.write_text(json.dumps(evalcfg, indent=2))

    digests = {"contract": canonical_digest(json.loads(eval_contract.read_text())),
               "brief": canonical_digest(json.loads(brief.read_text())),
               "evaluator_config": canonical_digest(evalcfg)}
    corpus_digest = byte_digest(contract)
    actions_ref = {"storage": "public", "path": "evals/review-catches-planted-defect/no-actions.txt",
                    "privateRef": None, "digest": byte_digest(HERE / "no-actions.txt")}

    isolation_template = json.loads((HERE / "isolation-manifest.json").read_text())
    isolation_template["modelSnapshot"] = model
    isolation_template["systemPromptDigest"] = evalcfg["systemPromptDigest"]
    isolation_template["contractDigest"] = digests["contract"]
    isolation_template["evaluatorConfigurationDigest"] = digests["evaluator_config"]

    isolation_refs, preflight_paths = {}, {}
    for arm, cfg in ARMS.items():
        # runId/conditionArm describe the arm this manifest covers, not a specific
        # trial -- prepare_shared runs once per twin-run invocation, so a manifest
        # written here is shared across every trial of this arm; naming it "{arm}-1"
        # would misleadingly imply it belongs to trial 1 only.
        manifest = dict(isolation_template, runId=arm, conditionArm=arm)
        manifest_path = out_dir / f"{arm}-isolation-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        # `path` must point at the file actually written above (with content matching
        # `digest`), not the static repo template -- resolving the template's path
        # would never reproduce this per-run, per-arm digest. out_dir is typically a
        # scratch/tempdir outside the repo, so this is an absolute path, not a
        # repo-relative one.
        isolation_refs[arm] = {"storage": "public",
                                "path": str(manifest_path),
                                "privateRef": None, "digest": canonical_digest(manifest)}
        probe = json.loads((HERE / f"probes/{arm}-probe.json").read_text())
        probes_path = out_dir / f"probes-{arm}.json"
        probes_path.write_text(json.dumps([probe]))
        legs = [control_leg("preflight-control-observe", False),
                control_leg("preflight-control-observe-2", False)]
        if arm == "mutated":
            legs.append(control_leg("mutated-witness", True))
        obs_path = out_dir / f"{arm}-observations.json"
        obs_path.write_text(json.dumps(legs))
        verdict_path = out_dir / f"{arm}-preflight-verdict.json"
        code, _, err = eq("preflight", "--contract", str(eval_contract), "--probes", str(probes_path),
                           "--observations", str(obs_path), "--run-id", f"{arm}-1", out=verdict_path)
        if code != 0:
            print(f"driver: preflight for {arm} arm exited {code} (informational; not fatal): {err.strip()}",
                  file=sys.stderr)
        preflight_paths[arm] = (verdict_path, manifest_path)
    return digests, corpus_digest, isolation_refs, actions_ref, preflight_paths, eval_contract, evalcfg_path


def score_one(out_dir, arm, trial, record, corpus_digest, preflight_verdict, isolation_manifest,
              eval_contract, evalcfg_path):
    record_path = out_dir / f"{arm}-trial{trial}-record.json"
    record_path.write_text(json.dumps(record, indent=2))
    evidence_path = out_dir / f"{arm}-trial{trial}-evidence-artifact.json"
    probe = HERE / f"probes/{arm}-probe.json"
    policy = HERE / "scoring-policy.json"
    code, _, err = eq("score", "--record", str(record_path), "--contract", str(eval_contract),
                       "--probe", str(probe), "--preflight-verdict", str(preflight_verdict),
                       "--policy", str(policy), "--isolation-manifest", str(isolation_manifest),
                       "--evaluator-configuration", str(evalcfg_path), "--corpus-digest", corpus_digest,
                       out=evidence_path)
    return code, record_path, evidence_path, err


def cmd_smoke():
    prefix = eval_quality_prefix()
    if prefix is None:
        sys.exit("driver: smoke: could not resolve the eval-quality install prefix "
                 "(pixi run -e local-recipes bash -lc 'command -v eval-quality' failed)")
    shipped = prefix / "lib/node_modules/eval-quality/corpus/dev/contracts/satisfied-declarations.json"
    ours = HERE / "contract.json"
    for label, path in (("shipped dev corpus (satisfied-declarations.json)", shipped),
                         ("this story's own contract.json", ours)):
        if not path.exists():
            sys.exit(f"driver: smoke: {label} not found at {path}")
        code, _, err = eq("compile", "--in", str(path))
        print(f"smoke: {label} -> compile exit {code}")
        if code != 0:
            sys.exit(f"driver: smoke: {label} failed to compile (exit {code}): {err.strip()}")
    print("smoke: both corpora compiled cleanly")


def cmd_twin_run(args):
    if args.trials < 1:
        sys.exit(f"driver: twin-run: --trials must be >= 1 (got {args.trials})")
    model = resolve_model(args.model)
    out_dir = Path(args.out_dir) if args.out_dir else Path(tempfile.mkdtemp(prefix="eval-quality-review-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"driver: model={model} out_dir={out_dir}")
    digests, corpus_digest, isolation_refs, actions_ref, preflight_paths, eval_contract, evalcfg_path = (
        prepare_shared(out_dir, model, args.max_budget_usd))

    catch_counts = {"clean": 0, "mutated": 0}
    worst_exit = 0
    for trial in range(1, args.trials + 1):
        for arm, cfg in ARMS.items():
            diff_path = HERE / "arms" / cfg["diff"]
            raw, stdout_text, rc, cost, wall = invoke_review(diff_path, model, args.max_budget_usd)
            verdict_path, manifest_path = preflight_paths[arm]
            record, hit = build_record(f"{arm}-{trial}", arm, cfg["probe_id"], trial, raw, cfg["defect_present"],
                                        digests, stdout_text, rc, cost, wall,
                                        isolation_refs[arm], actions_ref)
            code, record_path, evidence_path, err = score_one(
                out_dir, arm, trial, record, corpus_digest, verdict_path, manifest_path,
                eval_contract, evalcfg_path)
            catch_counts[arm] += 1 if hit else 0
            worst_exit = max(worst_exit, code)
            print(f"trial {trial} [{arm}]: cites-planted={hit} score-exit={code} "
                  f"record={record_path} evidence={evidence_path}")
            if err.strip():
                print(err.strip(), file=sys.stderr)

    mutated_hits, clean_hits = catch_counts["mutated"], catch_counts["clean"]
    if args.trials == 1:
        split_ok = mutated_hits == 1 and clean_hits == 0
        print(f"twin-run: mutated-arm-cites={mutated_hits == 1} clean-arm-cites={clean_hits == 1} "
              f"(expected split: mutated cites, clean does not -> {'OK' if split_ok else 'DID NOT REPLICATE THIS TRIAL'})")
    else:
        print(f"catch-rate: mutated {mutated_hits}/{args.trials}, clean false-positives {clean_hits}/{args.trials}")
    # Deliberately NOT sys.exit(worst_exit): the spec's own Verification section pins
    # this task to "expected: exit 0" for both the one-trial and --trials 3 cases, and
    # `eval-quality score`'s own AD-21 verdict is measurement data this pilot reports,
    # not a PR-style pass/fail this pixi task should propagate (spec's "Never let the
    # review process exited 0 alone satisfy the oracle" cuts the other way too: a
    # measured miss/CONCERNS/invalid on one trial is not a driver failure). Every
    # `score-exit` and the driver's own catch-rate line are printed above for a human
    # or a future gate to read; Warden, not this task, remains the sole PR verdict.
    print(f"driver: worst eval-quality score exit across all trials/arms was {worst_exit} "
          "(informational; see per-trial lines above -- this task always exits 0)")
    sys.exit(0)


def cmd_replay(record_arg):
    record_path = Path(record_arg)
    if not record_path.exists():
        sys.exit(f"driver: replay: no such sealed run record: {record_path}")
    out_dir = record_path.parent
    try:
        record = json.loads(record_path.read_text())
    except json.JSONDecodeError as exc:
        sys.exit(f"driver: replay: {record_path} is not valid JSON: {exc}")
    arm = record.get("conditionArm")
    if arm not in ARMS:
        sys.exit(f"driver: replay: record's conditionArm {arm!r} is not one of {list(ARMS)}")
    verdict_path = out_dir / f"{arm}-preflight-verdict.json"
    manifest_path = out_dir / f"{arm}-isolation-manifest.json"
    eval_contract = out_dir / "eval-contract.json"
    evalcfg_path = out_dir / "evaluator-configuration.json"
    for required in (verdict_path, manifest_path, eval_contract, evalcfg_path):
        if not required.exists():
            sys.exit(f"driver: replay: missing sibling artifact {required} "
                      "(replay needs the same --out-dir the original run wrote to)")
    corpus_digest = byte_digest(HERE / "contract.json")
    code, _, evidence_path, err = score_one(
        out_dir, arm, "replay", record, corpus_digest, verdict_path, manifest_path,
        eval_contract, evalcfg_path)
    print(f"replay: {arm} -> score exit {code}, evidence at {evidence_path} "
          "(no claude -p call was made)")
    if err.strip():
        print(err.strip(), file=sys.stderr)
    # Same reasoning as twin-run: the spec's own Verification section pins this task to
    # "expected: exit 0"; `eval-quality score`'s AD-21 verdict is measurement data,
    # printed above, not a pass/fail this pixi task propagates.
    sys.exit(0)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="mode", required=True)

    sub.add_parser("smoke", help="compile the shipped eval-quality dev corpus and this story's own contract")

    twin = sub.add_parser("twin-run", help="run edge-case-hunter against both arms and score them")
    twin.add_argument("--trials", type=int, default=1)
    twin.add_argument("--model")
    twin.add_argument("--max-budget-usd", type=float, default=2.0)
    twin.add_argument("--out-dir")

    replay = sub.add_parser("replay", help="re-score a previously sealed run record, no new claude -p call")
    replay.add_argument("record", help="path to a sealed run record written by a prior twin-run")

    args = ap.parse_args()
    if args.mode == "smoke":
        cmd_smoke()
    elif args.mode == "twin-run":
        cmd_twin_run(args)
    elif args.mode == "replay":
        cmd_replay(args.record)


if __name__ == "__main__":
    main()
