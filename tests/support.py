"""Shared test helpers: never touch the real home dir or the real claude CLI."""
import tempfile
from unittest.mock import patch


def forbid_runner(*args, **kwargs):
    raise AssertionError("real CLI runner must not be used in tests")


def no_external(root, reserved=(), executors=()):
    """Stand-in for plan_external: keeps unit tests off the real (large) submodules."""
    return {"files": {}, "meta": {}, "index": [], "catalog": {}, "skipped": {}, "active_skills": 0,
            "catalog_skills": 0, "catalog_agents": 0, "status": "unavailable: stubbed", "used_repos": []}


class Isolated:
    """Mixin: patches default home and runner used by the installer."""
    real_external = False

    def setUp(self):
        super().setUp()
        self._home = tempfile.TemporaryDirectory()
        self.addCleanup(self._home.cleanup)
        extra = () if self.real_external else (("scripts.project_install.plan_external", no_external),)
        for target, value in extra + (("scripts.project_install.default_home", lambda: self._home.name),
                              ("scripts.project_install.default_runner", forbid_runner),
                              ("scripts.project_install.shutil.which", lambda name: None)):
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
