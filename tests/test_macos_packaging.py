from __future__ import annotations

import unittest
from pathlib import Path


class MacOSPackagingTests(unittest.TestCase):
    def test_arm64_app_and_dmg_are_configured(self) -> None:
        root = Path(__file__).parents[1]
        spec = (root / "packaging/macos/script2video.spec").read_text(
            encoding="utf-8"
        )
        build_script = (root / "scripts/build-macos.sh").read_text(
            encoding="utf-8"
        )
        workflow = (root / ".github/workflows/build-windows.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn('target_arch="arm64"', spec)
        self.assertIn('"language_tags"', spec)
        self.assertIn('"pyopenjtalk"', spec)
        self.assertIn('"pypinyin"', spec)
        self.assertIn("Script2Video Studio.app", spec)
        self.assertIn("macOS-arm64.dmg", build_script)
        self.assertIn("language_tags/data/json/index.json", build_script)
        self.assertIn("runs-on: macos-15", workflow)
        self.assertIn("scripts/build-macos.sh", workflow)


if __name__ == "__main__":
    unittest.main()
