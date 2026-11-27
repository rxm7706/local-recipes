"""``scripts/nic_config_secret_scan.py`` and its pre-commit hook (steward Story 118.9, spec-pyforge-steward CAP-178).

No secret-shaped value enters a tracked NIC config: the hook scans each staged file under
``src/platform/deploy/nic/`` with ``steward keys audit --secrets``'s pattern table, read from ``keys.py``'s
source, and refuses a planted value. The tracked Hetzner profile names env-var names only and nic's own
``gitops/`` branch.
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "nic_config_secret_scan.py"
NIC_DIR = ROOT / "src" / "platform" / "deploy" / "nic"
PLANTED = "AGE-SECRET-KEY-1TEST00FAKE00PLACEHOLDER00NOTREAL00SYNTHETIC"


def _load():
    spec = importlib.util.spec_from_file_location("nic_config_secret_scan_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_the_pattern_table_is_the_one_keys_audit_uses() -> None:
    names = [name for name, _pattern in _load().load_patterns()]
    assert names == [
        "anthropic-api-key",
        "age-identity",
        "pem-private-key-header",
        "pem-block-base64",
        "github-token",
        "github-fine-grained-token",
        "hetzner-api-token",
    ]
    # Parity with the table keys itself compiles: the same pattern text and the same flags, so an
    # argument the source reader would drop cannot leave this hook scanning a different table.
    from pyforge.steward.keys import _SECRET_PATTERNS

    loaded = [(name, pattern.pattern, pattern.flags) for name, pattern in _load().load_patterns()]
    assert loaded == [(name, pattern.pattern, pattern.flags) for name, pattern in _SECRET_PATTERNS]


@pytest.mark.parametrize(
    "entry",
    [
        're.compile("a", flags=re.IGNORECASE)',
        're.compile("a", re.IGNORECASE)',
        're.compile(pattern="a")',
        're.match("a")',
    ],
)
def test_a_table_entry_with_an_argument_the_reader_would_drop_cannot_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], entry: str
) -> None:
    mod = _load()
    keys = tmp_path / "keys.py"
    keys.write_text(f'import re\n_SECRET_PATTERNS = (("x", {entry}),)\n', encoding="utf-8")
    with pytest.raises(ValueError):
        mod.load_patterns(keys)
    clean = tmp_path / "clean.yaml"
    clean.write_text("env: GITOPS_DEPLOY_KEY\n", encoding="utf-8")
    monkeypatch.setattr(mod, "KEYS_MODULE", keys)
    assert mod.main([str(clean)]) == 2
    assert "could not run" in capsys.readouterr().out


def test_a_planted_secret_is_refused_by_name_not_value(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = tmp_path / "my-nebari-hetzner.yaml"
    config.write_text(f"project_name: x\nrepository:\n  existing:\n    key: {PLANTED}\n", encoding="utf-8")
    assert _load().main([str(config)]) == 1
    out = capsys.readouterr().out
    assert f"{config}:4 matches the 'age-identity' plaintext-secret pattern" in out
    assert PLANTED not in out


def test_env_var_names_pass(tmp_path: Path) -> None:
    config = tmp_path / "clean.yaml"
    config.write_text("auth:\n  ssh:\n    env: GITOPS_DEPLOY_KEY\n", encoding="utf-8")
    assert _load().main([str(config)]) == 0


def test_a_missing_file_or_table_cannot_run(tmp_path: Path) -> None:
    mod = _load()
    assert mod.main([str(tmp_path / "absent.yaml")]) == 2
    (tmp_path / "keys.py").write_text("OTHER = 1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        mod.load_patterns(tmp_path / "keys.py")
    (tmp_path / "keys.py").write_text('_SECRET_PATTERNS = (("x", "not-a-call"),)\n', encoding="utf-8")
    with pytest.raises(ValueError):
        mod.load_patterns(tmp_path / "keys.py")
    (tmp_path / "keys.py").write_text('_SECRET_PATTERNS = (("x",),)\n', encoding="utf-8")
    with pytest.raises(ValueError):
        mod.load_patterns(tmp_path / "keys.py")
    (tmp_path / "keys.py").write_text("_SECRET_PATTERNS = []\n", encoding="utf-8")
    with pytest.raises(ValueError):
        mod.load_patterns(tmp_path / "keys.py")


def test_the_script_exits_one_on_a_planted_secret(tmp_path: Path) -> None:
    config = tmp_path / "leak.yaml"
    config.write_text(f"-----BEGIN OPENSSH PRIVATE KEY-----\n{PLANTED}\n", encoding="utf-8")
    proc = subprocess.run([sys.executable, str(SCRIPT), str(config)], capture_output=True, text=True, check=False)
    assert proc.returncode == 1
    assert "pem-private-key-header" in proc.stdout and PLANTED not in proc.stdout


def test_the_pre_commit_stage_runs_the_scan_over_the_nic_configs() -> None:
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    assert "pre-commit" in config["default_install_hook_types"]
    hooks = {hook["id"]: hook for repo in config["repos"] for hook in repo["hooks"]}
    hook = hooks["nic-config-secret-scan"]
    assert hook["entry"] == "scripts/nic_config_secret_scan.py"
    assert hook["language"] == "script" and hook["stages"] == ["pre-commit"]
    assert re.match(hook["files"], "src/platform/deploy/nic/my-nebari-hetzner.yaml")
    assert not re.match(hook["files"], "src/platform/config/flags.json")


def test_every_tracked_nic_config_is_clean() -> None:
    configs = sorted(NIC_DIR.glob("*.yaml"))
    assert configs
    assert _load().main([str(path) for path in configs]) == 0


def test_the_tracked_hetzner_config_uses_nics_branch_and_names_no_secret() -> None:
    text = (NIC_DIR / "my-nebari-hetzner.yaml").read_text(encoding="utf-8")
    document = yaml.safe_load(text)
    assert set(document["cluster"]) == {"hetzner"}
    existing = document["repository"]["existing"]
    assert existing["url"] == "git@github.com:rxm7706/local-recipes.git"
    assert existing["branch"] == existing["path"] == f"gitops/{document['project_name']}"
    assert existing["auth"] == {"ssh": {"env": "GITOPS_DEPLOY_KEY"}}
    assert "GIT_TOKEN" not in text
    # Operator-owned values are named placeholders on a reserved TLD, never invented.
    assert document["domain"].endswith(".invalid")
    assert document["certificate"]["acme"]["email"].endswith(".invalid")


def test_every_hook_type_is_named_where_a_reader_learns_the_hooks() -> None:
    text = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    types = yaml.safe_load(text)["default_install_hook_types"]
    assert types == ["pre-commit", "commit-msg", "pre-push"]
    assert "either policy hook" not in text  # three hook types, not two
    tutorial = (ROOT / "docs" / "tutorials" / "onboard-a-machine.md").read_text(encoding="utf-8")
    samples = re.findall(r"git-hooks: installed in the shared hooks directory: (.+)", tutorial)
    assert samples and all(sample.split(", ") == types for sample in samples)
