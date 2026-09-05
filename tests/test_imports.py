"""Import every module in the package.

This exists because of a real failure. `sqlalchemy`, `psycopg`, `alembic`, `numpy` and
`scikit-learn` went undeclared in `pyproject.toml` from the Postgres migration in
2026-08 until 2026-09-05: every development environment already had them through
Anaconda, and CI installed only what was declared but never imported a module that needed
them. The three test modules that existed covered `transform`, `lp` and `heuristic`, none
of which touches a database or a model. So CI was green for weeks on a package that could
not have been installed and run from a clean environment, which is the one thing CI was
supposed to prove.

Adding the missing pins fixes that instance. This test fixes the class: any module whose
imports are not satisfied by the declared dependencies now fails collection immediately,
whether or not anyone has written a test that exercises it.

It deliberately imports rather than merely finding modules. A module that imports cleanly
can still be broken, but a module that does not import cannot be run at all, and that is
the failure this is here to catch.
"""

import importlib
import pkgutil

import pytest

import gbmo

MODULES = sorted(
    module.name
    for module in pkgutil.walk_packages(gbmo.__path__, prefix="gbmo.")
    if not module.ispkg
)


def test_the_walk_found_something():
    """A failure to discover modules would make every test below vacuously pass."""
    assert len(MODULES) >= 10, MODULES


@pytest.mark.parametrize("module_name", MODULES)
def test_module_imports(module_name):
    importlib.import_module(module_name)
