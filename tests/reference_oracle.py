"""Opt-in access to the externally preserved original research program.

Normal framework tests do not require this artifact. Missing opt-in is reported
as an explicit skip only when a test asks to execute an original-source oracle.
"""
import os
from pathlib import Path
import unittest


def require_reference_dir() -> Path:
    value = os.environ.get("HYDROOPS_ANIK_SOURCE_DIR")
    if not value:
        raise unittest.SkipTest(
            "optional original-source oracle: set HYDROOPS_ANIK_SOURCE_DIR to the verified external bundle"
        )
    return Path(value).expanduser().resolve()


def load_anik(project_root):
    require_reference_dir()
    from examples.fe_walter.extensions.anik_v3_7 import load_anik as load_original
    return load_original(project_root)
