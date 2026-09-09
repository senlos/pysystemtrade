import unittest
from sysinit.futures.calculate_sp500_target import validate_target


class TargetValidationTests(unittest.TestCase):
    def test_finite_target_inside_buffers(self) -> None:
        validate_target(0.02, 0.01, 0.03)

    def test_nonfinite_rejected(self) -> None:
        for values in [(float("nan"), 0, 1), (0, -1, float("inf"))]:
            with self.assertRaises(ValueError):
                validate_target(*values)

    def test_inverted_or_excluding_buffers_rejected(self) -> None:
        for values in [(0, 1, -1), (2, 0, 1)]:
            with self.assertRaises(ValueError):
                validate_target(*values)
