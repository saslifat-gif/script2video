from __future__ import annotations

import unittest
from pathlib import Path


class WindowsPackagingTests(unittest.TestCase):
    def test_language_tags_registry_is_collected_and_verified(self) -> None:
        root = Path(__file__).parents[1]
        spec = (root / "packaging/windows/script2video.spec").read_text(
            encoding="utf-8"
        )
        project = (root / "pyproject.toml").read_text(encoding="utf-8")
        build_script = (root / "scripts/build-windows.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn('"language-tags>=1.3.1,<2"', project)
        self.assertIn('"misaki[ja,zh]>=0.9.4,<1"', project)
        self.assertIn('"language_tags"', spec)
        self.assertIn('"pyopenjtalk"', spec)
        self.assertIn('"pypinyin"', spec)
        self.assertIn(
            r"language_tags\data\json\index.json",
            build_script,
        )
        self.assertIn(
            "Packaged language-tags registry is missing",
            build_script,
        )


if __name__ == "__main__":
    unittest.main()
