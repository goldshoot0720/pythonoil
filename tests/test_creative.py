from pathlib import Path
import shutil
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil_tracker.creative import load_creative_notes, save_creative_notes
from oil_tracker.creative_art import save_reference_vector_art


class CreativeNotesTests(unittest.TestCase):
    def test_creative_notes_can_save_and_load(self) -> None:
        test_dir = Path("tests_tmp") / self._testMethodName
        if test_dir.exists():
            shutil.rmtree(test_dir)
        notes_path = test_dir / "creative_notes.txt"

        save_creative_notes("自由創作內容", notes_path)
        content = load_creative_notes(notes_path)

        self.assertEqual(content, "自由創作內容")

    def test_reference_vector_art_can_be_exported(self) -> None:
        test_dir = Path("tests_tmp") / self._testMethodName
        if test_dir.exists():
            shutil.rmtree(test_dir)
        svg_path = test_dir / "creative_vector_art.svg"

        output_path = save_reference_vector_art(svg_path)

        self.assertEqual(output_path, svg_path)
        self.assertTrue(svg_path.exists())
        self.assertIn("<svg", svg_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
