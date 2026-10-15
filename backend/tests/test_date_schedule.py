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


def test_generate_datewise_schedule_basic():
    # 2-week schedule from Monday 2026-10-05 to Friday 2026-10-16
    start = date(2026, 10, 5)   # Monday
    end = date(2026, 10, 16)    # Friday of next week (total 12 calendar days)
    # Weekdays: Mon, Wed, Fri have 2 periods each of "Math" and 1 of "CS Lab" (lab counts as 2 periods)
    weekdays = {
        "Monday": [TimetablePeriod(subject="Math", periods=1), TimetablePeriod(subject="CS Lab", periods=2)],
        "Wednesday": [TimetablePeriod(subject="Math", periods=1)],
        "Friday": [TimetablePeriod(subject="Physics", periods=1)],
    }
    no_class = {date(2026, 10, 7)}  # Wednesday holiday
    special = [
        SpecialWorkingDay(date=date(2026, 10, 10), mimic_weekday="Monday")  # Saturday mimics Monday
    ]

    counts, last_dates, teaching_days = generate_datewise_schedule(
        start_date=start,
        end_date=end,
        weekdays=weekdays,
        no_class_dates=no_class,
        special_working_days=special,
        subject_names={"Math", "CS Lab", "Physics"},
    )

    # Mondays: Oct 5, Oct 12 (2 days) -> Math=2, CS Lab=4
    # Special Sat Oct 10 mimics Monday -> Math=1, CS Lab=2
    # Wednesdays: Oct 7 (Holiday, 0 classes), Oct 14 -> Math=1
    # Fridays: Oct 9, Oct 16 (2 days) -> Physics=2
    # Total Math = 2 (Mondays) + 1 (Sat special) + 1 (Wed) = 4
    # Total CS Lab = 4 (Mondays) + 2 (Sat special) = 6
    # Total Physics = 2
    assert counts["Math"] == 4
    assert counts["CS Lab"] == 6
    assert counts["Physics"] == 2
    assert last_dates["Physics"] == date(2026, 10, 16)
    assert last_dates["Math"] == date(2026, 10, 14)


def test_calculate_semester_projections_multi_subject():
    start = date(2026, 10, 5)
    end = date(2026, 10, 16)
    req = SemesterPlanRequest(
        target_percentage=80.0,
        start_date=start,
        end_date=end,
        weekdays={
            "Monday": [TimetablePeriod(subject="Math", periods=2)],
            "Tuesday": [TimetablePeriod(subject="Physics", periods=2)],
        },
        no_class_dates=[],
        special_working_days=[],
        subjects=[
            SubjectAttendanceState(name="Math", present=18, total=20),
            SubjectAttendanceState(name="Physics", present=5, total=20),
        ],
    )

    res = calculate_semester_projections(req)
    assert len(res.subjects) == 2

    math_sub = next(s for s in res.subjects if s.name == "Math")
    # Math has 2 Mondays: Oct 5, Oct 12. 2 periods each = 4 future classes
    # Total = 20 + 4 = 24. Target 80% of 24 = 19.2 -> 20. Present = 18.
    # To attend = 2. Can skip = 4 - 2 = 2.
    assert math_sub.future_classes == 4
    assert math_sub.final_total_classes == 24
    assert math_sub.classes_to_attend == 2
    assert math_sub.classes_can_skip == 2
    assert math_sub.achievable is True

    phys_sub = next(s for s in res.subjects if s.name == "Physics")
    # Physics: 5 present / 20 total. 2 Tuesdays = 4 future. Final total = 24.
    # Target 80% of 24 = 19.2 -> 20. Present = 5. Needed = 15. Future = 4.
    # Target not achievable!
    assert phys_sub.achievable is False
    assert phys_sub.classes_can_skip == 0
