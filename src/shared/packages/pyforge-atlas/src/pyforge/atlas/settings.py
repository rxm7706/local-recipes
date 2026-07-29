"""Project settings. There is no need to edit this file unless you want to change values
from the Kedro defaults. For further information, including these default values, see
https://docs.kedro.org/en/stable/configure/configuration_basics/#configuration"""

import os

# Instantiated project hooks.
# Story A3 (assumption A3-1): ProjectHooks.after_catalog_created injects each
# IncrementalParquetDataset's per-dataset TTL from params:ttls.<name>, keeping
# parameters.yml the single source of truth (FR-3/AD-5). Decoupled from both A3
# gates — the resolution test uses DataCatalog.from_config directly (hooks do not
# run there) and the unit tests set ttl_seconds explicitly.
# Hooks are executed in a Last-In-First-Out (LIFO) order.
from pyforge.atlas.hooks import ProjectHooks

# Story E2 (FR-12, AD-6/AD-23): observability instrumentation declared ONCE here
# so EVERY entry point inherits it — a `kedro run` picks up settings HOOKS
# natively, and a Dagster run picks them up too. NOT because the translator "runs
# each node through KedroSession.run" — it does not; kedro-dagster calls
# `Node.run()` directly and fires the hooks itself from dedicated ops. What every
# entry point actually shares is the kedro HOOK MANAGER, which is what these
# registrations ride (corrected by Story 10.6; the same false claim was removed
# from orchestration/definitions.py). Constructed with no args → both backends
# default to no-op/offline (no network at import or run); the gate injects
# in-memory captors. See pyforge.atlas.observability.
from pyforge.atlas.observability import AtlasObservabilityHooks

# Story F2 (FR-10, AD-9/AD-20/AD-23): the data-validation hook rides EVERY entry
# point too — a `kedro run` AND the C1 Dagster plane both validate node outputs
# against their per-dataset pandera contract, halting BEFORE bad data persists and
# raising an A2A alert. Constructed with no args → the shipped default: a pandera
# validator over the (empty) DEFAULT_CONTRACTS registry with a no-op alert sink, so
# the default path is offline and can never false-halt until a contract is declared.
# See pyforge.atlas.validation.
from pyforge.atlas.validation import DataValidationHooks

# Story 10.6 (AD-23, audit AUD-ATLAS-046): run admission declared ONCE here so EVERY
# entry point inherits it — the `kedro run` CLI, the seven MCP `run_*` tools, and the
# Dagster plane all dispatch through the same hook manager. One OS file lock per output
# dataset; reject-fast by default, bounded wait opt-in via
# `--params admission_wait_seconds=<n>`. Constructed with no args → the lock root
# resolves per-run from `run_params["project_path"]` (PROJECT-anchored, never
# CWD-relative — a CWD-relative root would silently void admission between two
# processes writing the same Parquet from different directories).
#
# Appended LAST on purpose: kedro registers this tuple in order and pluggy dispatches
# LIFO, so admission is acquired BEFORE every other before_pipeline_run and released
# BEFORE every other after_pipeline_run. See pyforge.atlas.admission for the boundaries
# that ordering creates.
from pyforge.atlas.admission import RunAdmissionHooks

HOOKS = (
    ProjectHooks(),
    AtlasObservabilityHooks(),
    DataValidationHooks(),
    RunAdmissionHooks(),
)

# Installed plugins for which to disable hook auto-registration.
# DISABLE_HOOKS_FOR_PLUGINS = ("kedro-viz",)

# Class that manages the KedroSession.
# from kedro.framework.session import KedroSession
# SESSION_CLASS = KedroSession

# Class that manages storing KedroSession data.
# from kedro.framework.session.store import BaseSessionStore
# SESSION_STORE_CLASS = BaseSessionStore
# Keyword arguments to pass to the `SESSION_STORE_CLASS` constructor.
# SESSION_STORE_ARGS = {
#     "path": "./sessions"
# }

# Directory that holds configuration.
# CONF_SOURCE = "conf"

# Class that manages how configuration is loaded.
# from kedro.config import OmegaConfigLoader

# CONFIG_LOADER_CLASS = OmegaConfigLoader


def _env_or(var: str, default: str = "") -> str:
    """Endpoint-override resolver (Story A2; spine AD-2/AD-13).

    Explicit environment always beats the declared public default
    (spine "Config & profiles" row — ``os.environ.setdefault`` semantics).
    Used by ``conf/base/globals.yml`` to make every ``<HOST>_BASE_URL``
    override point env-var-overridable without hardcoding hosts in the
    catalog (the legacy ``resolve_*_urls`` convention carried forward).

    An EMPTY-string env var is treated as unset (review-pass P6):
    ``export CONDA_FORGE_BASE_URL=""`` must fall back to the public
    default, never inject an empty endpoint base into every URL.
    """
    val = os.environ.get(var)
    return val if val else default


# Keyword arguments to pass to the `CONFIG_LOADER_CLASS` constructor.
CONFIG_LOADER_ARGS = {
    "base_env": "base",
    "default_run_env": "local",
    # A2 (AD-2/AD-13): the env_or resolver backing the endpoint-base
    # globals. kedro-catalog-check exercises this exact wiring.
    "custom_resolvers": {"env_or": _env_or},
    # "config_patterns": {
    #     "spark" : ["spark*/"],
    #     "parameters": ["parameters*", "parameters*/**", "**/parameters*"],
    # }
}

# Class that manages Kedro's library components.
# from kedro.framework.context import KedroContext
# CONTEXT_CLASS = KedroContext

# Class that manages the Data Catalog.
# from kedro.io import DataCatalog
# DATA_CATALOG_CLASS = DataCatalog
