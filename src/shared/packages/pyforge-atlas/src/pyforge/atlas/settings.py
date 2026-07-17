"""Project settings. There is no need to edit this file unless you want to change values
from the Kedro defaults. For further information, including these default values, see
https://docs.kedro.org/en/stable/configure/configuration_basics/#configuration"""

import os

# Instantiated project hooks.
# For example, after creating a hooks.py and defining a ProjectHooks class there, do
# from pyforge.atlas.hooks import ProjectHooks
# Hooks are executed in a Last-In-First-Out (LIFO) order.
# HOOKS = (ProjectHooks(),)

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
    """
    return os.environ.get(var, default)


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
