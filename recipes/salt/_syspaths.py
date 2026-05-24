import os
import sys

ROOT_DIR = sys.exec_prefix

# Copied from salt source: salt/syspaths.py
CONFIG_DIR = os.path.join(ROOT_DIR, 'etc', 'salt')
CACHE_DIR = os.path.join(ROOT_DIR, 'var', 'cache', 'salt')
SOCK_DIR = os.path.join(ROOT_DIR, 'var', 'run', 'salt')
SRV_ROOT_DIR = os.path.join(ROOT_DIR, 'srv')
BASE_FILE_ROOTS_DIR = os.path.join(SRV_ROOT_DIR, 'salt')
BASE_PILLAR_ROOTS_DIR = os.path.join(SRV_ROOT_DIR, 'pillar')
BASE_MASTER_ROOTS_DIR = os.path.join(SRV_ROOT_DIR, 'salt-master')
BASE_THORIUM_ROOTS_DIR = os.path.join(SRV_ROOT_DIR, 'thorium')
LOGS_DIR = os.path.join(ROOT_DIR, 'var', 'log', 'salt')
PIDFILE_DIR = os.path.join(ROOT_DIR, 'var', 'run')
SPM_PARENT_PATH = os.path.join(SRV_ROOT_DIR, 'spm')
SPM_FORMULA_PATH = os.path.join(SPM_PARENT_PATH, 'salt')
SPM_PILLAR_PATH = os.path.join(SPM_PARENT_PATH, 'pillar')
SPM_REACTOR_PATH = os.path.join(SPM_PARENT_PATH, 'reactor')
SHARE_DIR = os.path.join(ROOT_DIR, 'usr', 'share', 'salt')
LIB_STATE_DIR = CONFIG_DIR
HOME_DIR = os.path.expanduser('~')
