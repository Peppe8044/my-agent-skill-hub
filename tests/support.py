"""Shared test helpers: never touch the real home dir or the real claude CLI."""
import tempfile
from unittest.mock import patch


def forbid_runner(*args, **kwargs):
    raise AssertionError("real CLI runner must not be used in tests")


class Isolated:
    """Mixin: patches default home and runner used by the installer."""
    def setUp(self):
        super().setUp()
        self._home = tempfile.TemporaryDirectory()
        self.addCleanup(self._home.cleanup)
        for target, value in (("scripts.project_install.default_home", lambda: self._home.name),
                              ("scripts.project_install.default_runner", forbid_runner),
                              ("scripts.project_install.shutil.which", lambda name: None)):
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
