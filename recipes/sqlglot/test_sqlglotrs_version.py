from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from importlib.metadata import version

HERE = Path(__file__).parent
CARGO_TOML = HERE / "sqlglotrs/Cargo.toml"


def test_sqlglot_uses_rs_tokens():
    from sqlglot.tokens import USE_RS_TOKENIZER

    assert USE_RS_TOKENIZER, """sqlglot did not detect the sqlglotrs tokenizer"""


def test_sqlglot_version_matches_cargo_toml():
    cargo_toml = tomllib.load(CARGO_TOML.open("rb"))
    expected_version = cargo_toml["package"]["version"]
    observed_version = version("sqlglotrs")
    assert observed_version == expected_version, f"""
        Please update `meta.yaml` to contain:

            {{% set sqlglotrs_version = "{expected_version}" %}}
        """
