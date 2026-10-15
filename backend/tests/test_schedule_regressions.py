import pytest
from datetime import date
from backend.attendance_engine import (
    generate_datewise_schedule,
    calculate_semester_projections,
    SemesterPlanRequest,
    SubjectAttendanceState,
    TimetablePeriod,
    SpecialWorkingDay,
)


def test_special_working_day_replaces_or_augments_without_double_counting():
    """Verify that a special working day (e.g. Saturday) mimicking Monday only adds

    periods once, and if Monday is a holiday, regular Monday has 0 classes.
    """
    start = date(2026, 10, 5)   # Monday
    end = date(2026, 10, 11)    # Sunday (1 week)
    weekdays = {
        "Monday": [TimetablePeriod(subject="Algorithms", periods=2)],
        "Tuesday": [],
        "Wednesday": [],
        "Thursday": [],
        "Friday": [],
        "Saturday": [],
        "Sunday": [],
    }

    # Case A: Regular Monday + Saturday mimicking Monday -> 2 + 2 = 4 periods
    special_sat = [SpecialWorkingDay(date=date(2026, 10, 10), mimic_weekday="Monday")]
    counts, _, teaching_days = generate_datewise_schedule(
        start_date=start,
        end_date=end,
        weekdays=weekdays,
        no_class_dates=set(),
        special_working_days=special_sat,
        subject_names={"Algorithms"},
    )
    assert counts["Algorithms"] == 4
    assert teaching_days == 2  # Mon and Sat

    # Case B: Monday is a declared holiday, but Saturday compensates
    counts_b, _, teaching_days_b = generate_datewise_schedule(
        start_date=start,
        end_date=end,
        weekdays=weekdays,
        no_class_dates={date(2026, 10, 5)},  # Mon holiday
        special_working_days=special_sat,
        subject_names={"Algorithms"},
    )
    # Mon = 0 (holiday), Sat = 2
    assert counts_b["Algorithms"] == 2
    assert teaching_days_b == 1  # Only Saturday had classes


def test_multi_period_lab_counting():
    """Verify multi-period labs (e.g. 3 periods) are counted as 3 attendance units per occurrence."""
    start = date(2026, 10, 5)
    end = date(2026, 10, 19) # 3 Mondays (Oct 5, 12, 19)
    weekdays = {
        "Monday": [TimetablePeriod(subject="Operating Systems Lab", periods=3)],
        "Tuesday": [], "Wednesday": [], "Thursday": [], "Friday": [], "Saturday": [], "Sunday": []
    }
    counts, last_dates, _ = generate_datewise_schedule(
        start_date=start,
        end_date=end,
        weekdays=weekdays,
        no_class_dates=set(),
        special_working_days=[],
        subject_names={"Operating Systems Lab"},
    )
    # 3 occurrences * 3 periods = 9
    assert counts["Operating Systems Lab"] == 9
    assert last_dates["Operating Systems Lab"] == date(2026, 10, 19)


def test_subject_last_class_differs_from_semester_end():
    """Verify distinction between last working day of semester and last class of an individual subject."""
    start = date(2026, 10, 5)   # Monday
    end = date(2026, 10, 16)    # Friday (Semester end)
    # Math meets only on Monday; Physics meets on Friday
    weekdays = {
        "Monday": [TimetablePeriod(subject="Math", periods=1)],
        "Friday": [TimetablePeriod(subject="Physics", periods=1)],
        "Tuesday": [], "Wednesday": [], "Thursday": [], "Saturday": [], "Sunday": []
    }
    _, last_dates, _ = generate_datewise_schedule(
        start_date=start,
        end_date=end,
        weekdays=weekdays,
        no_class_dates=set(),
        special_working_days=[],
        subject_names={"Math", "Physics"},
    )
    # Math's last class is Monday Oct 12, whereas semester last working day is Friday Oct 16
    assert last_dates["Math"] == date(2026, 10, 12)
    assert last_dates["Physics"] == date(2026, 10, 16)
