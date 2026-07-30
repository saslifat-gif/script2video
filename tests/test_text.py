from __future__ import annotations

import unittest

from script2video.text import split_text_scenes


class TextSceneTests(unittest.TestCase):
    def test_splits_complete_script_sentence_by_sentence(self) -> None:
        scenes = split_text_scenes(
            "Welcome to the show. This is scene two! Is this scene three? Yes."
        )

        self.assertEqual(
            scenes,
            [
                "Welcome to the show.",
                "This is scene two!",
                "Is this scene three?",
                "Yes.",
            ],
        )

    def test_splits_chinese_sentence_punctuation(self) -> None:
        self.assertEqual(
            split_text_scenes("欢迎来到节目。现在开始！你准备好了吗？"),
            ["欢迎来到节目。", "现在开始！", "你准备好了吗？"],
        )

    def test_keeps_abbreviations_and_decimals_inside_sentence(self) -> None:
        self.assertEqual(
            split_text_scenes("Dr. Smith measured 3.5 seconds. Then we continued."),
            ["Dr. Smith measured 3.5 seconds.", "Then we continued."],
        )

    def test_sentence_mode_ignores_layout_newlines(self) -> None:
        self.assertEqual(
            split_text_scenes("Opening title\n\nThe story begins"),
            ["Opening title The story begins"],
        )

    def test_supports_selectable_split_patterns(self) -> None:
        text = "First line\nSecond line\n\nLast paragraph"

        self.assertEqual(
            split_text_scenes(text, mode="paragraph"),
            ["First line Second line", "Last paragraph"],
        )
        self.assertEqual(
            split_text_scenes(text, mode="line"),
            ["First line", "Second line", "Last paragraph"],
        )
        self.assertEqual(
            split_text_scenes(text, mode="whole"),
            ["First line Second line Last paragraph"],
        )

    def test_rejects_unknown_split_pattern(self) -> None:
        with self.assertRaisesRegex(ValueError, "Scene split mode"):
            split_text_scenes("Hello.", mode="unknown")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
