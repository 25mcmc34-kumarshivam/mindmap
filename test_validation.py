"""CLI validation tests that require no Node or browser installation."""
import unittest

from markmap_to_pdf import MarkmapError, build_parser, validate


class NumericValidationTests(unittest.TestCase):
    def test_defaults_are_valid(self):
        validate(build_parser().parse_args(["sample.md"]))

    def test_nonfinite_values_are_rejected(self):
        for option in ("scale", "zoom", "padding",
                       "spacing-vertical", "spacing-horizontal", "timeout"):
            for value in ("nan", "inf", "-inf"):
                with self.subTest(option=option, value=value):
                    args = build_parser().parse_args(
                        ["sample.md", f"--{option}={value}"])
                    with self.assertRaisesRegex(MarkmapError, "must be finite"):
                        validate(args)


if __name__ == "__main__":
    unittest.main()
