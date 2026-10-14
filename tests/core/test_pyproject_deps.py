"""T101 (AC-EVL-06): CI installs from pyproject, so it must declare what src imports."""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Import name to the distribution that provides it, where the two differ.
DIST_OF = {"argon2": "argon2-cffi", "jwt": "pyjwt", "yaml": "pyyaml", "dotenv": "pydantic-settings"}
# Installed by a declared package, so listing them again would only be noise.
TRANSITIVE = {"pydantic", "starlette"}


def declared() -> set[str]:
    """Distribution names in pyproject dependencies and the dev extra, normalized."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    specs = project["dependencies"] + project["optional-dependencies"]["dev"]
    return {re.split(r"[<>=\[ ]", spec)[0].lower().replace("_", "-") for spec in specs}


def imported_by_src() -> set[str]:
    """Top level third party module names imported anywhere under src/."""
    modules: set[str] = set()
    for path in (ROOT / "src").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                modules |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules.add(node.module.split(".")[0])
    return {m for m in modules if m not in sys.stdlib_module_names and m != "docdesk"}


def test_ac_evl_06_pyproject_declares_every_third_party_import_of_src() -> None:
    names = declared()
    missing = sorted(
        module
        for module in imported_by_src() - TRANSITIVE
        if DIST_OF.get(module, module).lower().replace("_", "-") not in names
    )
    assert not missing, f"imported by src but not declared in pyproject.toml: {missing}"


def test_ac_evl_06_pyproject_declares_the_redis_client_celery_uses_as_broker() -> None:
    assert "redis" in declared()
