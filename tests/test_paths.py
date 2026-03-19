from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil_tracker.paths import app_base_dir, default_db_path, default_log_path


class AppPathTests(unittest.TestCase):
    def test_defaults_use_current_directory_when_not_frozen(self) -> None:
        expected_base = Path.cwd()

        self.assertEqual(app_base_dir(), expected_base)
        self.assertEqual(default_db_path(), expected_base / "data" / "oil_prices.db")
        self.assertEqual(default_log_path(), expected_base / "data" / "oil_tracker.log")

    def test_defaults_use_executable_directory_when_frozen(self) -> None:
        frozen_exe = Path("C:/Apps/PythonOilGUI.exe")

        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(frozen_exe)):
            self.assertEqual(app_base_dir(), frozen_exe.parent)
            self.assertEqual(default_db_path(), frozen_exe.parent / "data" / "oil_prices.db")
            self.assertEqual(default_log_path(), frozen_exe.parent / "data" / "oil_tracker.log")


if __name__ == "__main__":
    unittest.main()
