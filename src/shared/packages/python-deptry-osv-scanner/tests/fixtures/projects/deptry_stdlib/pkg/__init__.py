# argparse is imported (so it is not DEP002-unused) but it ships in the
# standard library -> deptry DEP005. requests is declared + imported (clean).
import argparse
import requests

__all__ = ["argparse", "requests"]
