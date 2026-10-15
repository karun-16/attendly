import pytest
from backend.attendance_engine import (
    calculate_quick_attendance,
    QuickCalculatorInput,
)


def test_quick_calculator_standard():
    # 43 attended, 56 conducted, 40 future, 80% target
    # Total = 96, 80% of 96 = 76.8 -> ceil(76.8 - 43) = ceil(33.8) = 34
    # Skips = 40 - 34 = 6
    data = QuickCalculatorInput(present=43, total=56, future=40, target_percentage=80)
    result = calculate_quick_attendance(data)
    assert result.current_percentage == 76.79
    assert result.min_future_classes_to_attend == 34
    assert result.max_future_classes_can_skip == 6
    assert result.achievable is True


def test_quick_calculator_exact_threshold():
    # P = 8, T = 10, N = 0, Target = 80%
    # Exactly 80% attendance with zero future classes
    data = QuickCalculatorInput(present=8, total=10, future=0, target_percentage=80)
    result = calculate_quick_attendance(data)
    assert result.current_percentage == 80.0
    assert result.min_future_classes_to_attend == 0
    assert result.max_future_classes_can_skip == 0
    assert result.achievable is True


def test_quick_calculator_unachievable():
    # P = 10, T = 50 (20%), N = 10 future classes, Target = 75%
    # Final total = 60. 75% of 60 = 45. Needed = 45 - 10 = 35. But only 10 future classes!
    data = QuickCalculatorInput(present=10, total=50, future=10, target_percentage=75)
    result = calculate_quick_attendance(data)
    assert result.achievable is False
    assert result.max_future_classes_can_skip == 0
    assert "cannot be reached" in result.status_message


def test_quick_calculator_zero_total():
    # Semester hasn't started yet: 0 attended, 0 conducted, 20 future, 75% target
    # Final total = 20. 75% of 20 = 15. Needed = 15. Skips = 5.
    data = QuickCalculatorInput(present=0, total=0, future=20, target_percentage=75)
    result = calculate_quick_attendance(data)
    assert result.current_percentage == 100.0
    assert result.min_future_classes_to_attend == 15
    assert result.max_future_classes_can_skip == 5
    assert result.achievable is True


def test_quick_calculator_100_percent():
    # 100% target: P = 10, T = 10, N = 5, Target = 100%
    # Final total = 15. Needed = 15 - 10 = 5. Skips = 0.
    data = QuickCalculatorInput(present=10, total=10, future=5, target_percentage=100)
    result = calculate_quick_attendance(data)
    assert result.min_future_classes_to_attend == 5
    assert result.max_future_classes_can_skip == 0
    assert result.achievable is True


def test_quick_calculator_custom_target():
    # Custom target e.g. 78.5%
    # P = 20, T = 25, N = 15, Target = 78.5%
    # Final total = 40. 78.5% of 40 = 31.4 -> ceil = 32. Needed = 32 - 20 = 12. Skips = 3.
    data = QuickCalculatorInput(present=20, total=25, future=15, target_percentage=78.5)
    result = calculate_quick_attendance(data)
    assert result.min_future_classes_to_attend == 12
    assert result.max_future_classes_can_skip == 3
    assert result.achievable is True


def test_quick_calculator_invalid_inputs():
    # Present > Total
    with pytest.raises(ValueError):
        calculate_quick_attendance(QuickCalculatorInput(present=30, total=20, future=5, target_percentage=80))

    # Negative present
    with pytest.raises(Exception):
        QuickCalculatorInput(present=-1, total=10, future=5, target_percentage=80)

    # Target > 100
    with pytest.raises(Exception):
        QuickCalculatorInput(present=5, total=10, future=5, target_percentage=105)
