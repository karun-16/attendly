"""Attendance calculation engine for Attendly.

Implements deterministic attendance formulas and date-wise schedule generation.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any
from pydantic import BaseModel, Field


def canonical_subject_name(subject: str) -> str:
    """Merge theory and lab timetable labels into one attendance subject."""
    clean = " ".join(subject.strip().replace("_", " ").replace("-", " ").split())
    key = clean.lower()
    for suffix in (" laboratory", " lab"):
        if key.endswith(suffix):
            key = key[:-len(suffix)].strip()
            break
    aliases = {
        "wt": "Web Technologies",
        "web technologies": "Web Technologies",
        "web tech": "Web Technologies",
        "ml": "Machine Learning",
        "machine learning": "Machine Learning",
        "ai": "Artificial Intelligence",
        "artificial intelligence": "Artificial Intelligence",
        "toc": "Theory of Computation",
        "theory of computation": "Theory of Computation",
        "lrre": "Logical Reasoning and Recruitment Essentials",
        "logical reasoning": "Logical Reasoning and Recruitment Essentials",
        "logical reasoning and recruitment essentials": "Logical Reasoning and Recruitment Essentials",
        "cdct": "Campus Recruitment Training",
        "campus recruitment training": "Campus Recruitment Training",
    }
    return aliases.get(key, clean)


class QuickCalculatorInput(BaseModel):
    present: int = Field(ge=0, description="Classes attended so far (P)")
    total: int = Field(ge=0, description="Total classes conducted so far (T)")
    future: int = Field(ge=0, description="Future classes scheduled (N)")
    target_percentage: float = Field(gt=0, le=100, description="Target percentage (e.g., 75, 80, 85, 90 or custom)")


class QuickCalculatorResult(BaseModel):
    present: int
    total: int
    future: int
    target_percentage: float
    current_percentage: float
    final_total_classes: int
    projected_percentage_if_attend_all: float
    min_future_classes_to_attend: int
    max_future_classes_can_skip: int
    achievable: bool
    status_message: str


def calculate_quick_attendance(data: QuickCalculatorInput) -> QuickCalculatorResult:
    """Calculate attendance metrics according to strict mathematical specification.

    Let:
      P = classes attended so far
      T = total classes conducted so far
      N = future classes scheduled
      R = required attendance expressed as a decimal (target_percentage / 100.0)

    Current attendance:
      100 * P / T (or 100.0 if T == 0)

    Final total classes:
      T + N

    Minimum future classes that must be attended:
      max(0, ceil(R * (T + N) - P))

    Maximum future classes that can be skipped:
      N - minimum_future_classes_required
    """
    if data.present > data.total:
        raise ValueError("Classes attended (P) cannot exceed total classes conducted (T).")

    p = data.present
    t = data.total
    n = data.future
    r = data.target_percentage / 100.0

    current_pct = (p / t * 100.0) if t > 0 else 100.0
    final_total = t + n

    projected_if_all = ((p + n) / final_total * 100.0) if final_total > 0 else 100.0

    if final_total == 0:
        # No classes held and no classes scheduled
        return QuickCalculatorResult(
            present=p,
            total=t,
            future=n,
            target_percentage=data.target_percentage,
            current_percentage=100.0,
            final_total_classes=0,
            projected_percentage_if_attend_all=100.0,
            min_future_classes_to_attend=0,
            max_future_classes_can_skip=0,
            achievable=True,
            status_message="No classes conducted or scheduled.",
        )

    # Use exact ceil with float tolerance protection to avoid floating-point imprecision
    # e.g., 0.80 * 10 = 8.000000000000002, ceil must remain 8, not 9
    raw_required = r * final_total - p
    epsilon = 1e-9
    if abs(raw_required - round(raw_required)) < epsilon:
        required_int = int(round(raw_required))
    else:
        required_int = math.ceil(raw_required)

    min_to_attend = max(0, required_int)
    achievable = min_to_attend <= n
    can_skip = max(0, n - min_to_attend) if achievable else 0

    if not achievable:
        status_msg = (
            f"Target {data.target_percentage:g}% cannot be reached within the {n} scheduled future classes. "
            f"Maximum achievable attendance is {projected_if_all:.2f}% even with 100% future attendance."
        )
    elif can_skip > 0:
        status_msg = (
            f"You can safely miss up to {can_skip} of the next {n} classes and maintain "
            f"at least {data.target_percentage:g}%."
        )
    else:
        status_msg = (
            f"You must attend at least {min_to_attend} of the next {n} classes. "
            f"You cannot afford to miss any classes to reach {data.target_percentage:g}%."
        )

    return QuickCalculatorResult(
        present=p,
        total=t,
        future=n,
        target_percentage=data.target_percentage,
        current_percentage=round(current_pct, 2),
        final_total_classes=final_total,
        projected_percentage_if_attend_all=round(projected_if_all, 2),
        min_future_classes_to_attend=min_to_attend if achievable else n,
        max_future_classes_can_skip=can_skip,
        achievable=achievable,
        status_message=status_msg,
    )


WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


class TimetablePeriod(BaseModel):
    subject: str
    periods: int = Field(default=1, ge=1, le=12)


class SubjectAttendanceState(BaseModel):
    name: str
    present: int = Field(default=0, ge=0)
    total: int = Field(default=0, ge=0)


class SpecialWorkingDay(BaseModel):
    date: date
    # Either mimics a specific weekday timetable or defines explicit subject periods
    mimic_weekday: str | None = None
    subject: str | None = None
    periods: int = Field(default=1, ge=1, le=12)


class SemesterPlanRequest(BaseModel):
    target_percentage: float = Field(gt=0, le=100)
    start_date: date
    end_date: date
    future_start_date: date | None = None
    weekdays: dict[str, list[TimetablePeriod]] = Field(default_factory=dict)
    no_class_dates: list[date] = Field(default_factory=list)
    special_working_days: list[SpecialWorkingDay] = Field(default_factory=list)
    subjects: list[SubjectAttendanceState] = Field(default_factory=list)


class SubjectProjectionResult(BaseModel):
    name: str
    present: int
    total: int
    current_percentage: float
    future_classes: int
    final_total_classes: int
    projected_if_attend_all: float
    classes_to_attend: int
    classes_can_skip: int
    achievable: bool
    last_scheduled_class_date: date | None = None
    warning: str | None = None


class SemesterPlanResponse(BaseModel):
    target_percentage: float
    start_date: date
    end_date: date
    total_teaching_days: int
    subjects: list[SubjectProjectionResult]
    warnings: list[str] = Field(default_factory=list)


def generate_datewise_schedule(
    start_date: date,
    end_date: date,
    weekdays: dict[str, list[TimetablePeriod]],
    no_class_dates: set[date],
    special_working_days: list[SpecialWorkingDay],
    subject_names: set[str],
) -> tuple[dict[str, int], dict[str, date | None], int]:
    """Simulate every single date from start_date to end_date.

    Returns:
      (counts_per_subject, last_class_date_per_subject, total_teaching_days)
    """
    counts: dict[str, int] = {name: 0 for name in subject_names}
    last_class_dates: dict[str, date | None] = {name: None for name in subject_names}

    special_by_date: dict[date, list[SpecialWorkingDay]] = {}
    for sw in special_working_days:
        special_by_date.setdefault(sw.date, []).append(sw)

    total_teaching_days = 0
    current = start_date

    while current <= end_date:
        is_holiday = current in no_class_dates
        specials = special_by_date.get(current, [])

        day_had_classes = False

        if not is_holiday:
            w_name = WEEKDAY_NAMES[current.weekday()]
            day_periods = weekdays.get(w_name, [])

            for item in day_periods:
                s_name = canonical_subject_name(item.subject)
                if s_name in counts:
                    counts[s_name] += item.periods
                    last_class_dates[s_name] = current
                    day_had_classes = True

        # Special working days apply even if regular weekday was non-teaching (or holiday override)
        for sw in specials:
            if sw.mimic_weekday and sw.mimic_weekday in weekdays:
                for item in weekdays[sw.mimic_weekday]:
                    s_name = item.subject.strip()
                    if s_name in counts:
                        counts[s_name] += item.periods
                        last_class_dates[s_name] = current
                        day_had_classes = True
            elif sw.subject and canonical_subject_name(sw.subject) in counts:
                s_name = canonical_subject_name(sw.subject)
                counts[s_name] += sw.periods
                last_class_dates[s_name] = current
                day_had_classes = True

        if day_had_classes:
            total_teaching_days += 1

        current += timedelta(days=1)

    return counts, last_class_dates, total_teaching_days


def calculate_semester_projections(payload: SemesterPlanRequest) -> SemesterPlanResponse:
    """Calculate date-wise projections for all subjects across the semester."""
    if payload.end_date < payload.start_date:
        raise ValueError("Semester last working day must be on or after start date.")
    if not payload.subjects:
        raise ValueError("At least one subject is required for semester projection.")

    for sub in payload.subjects:
        if sub.present > sub.total:
            raise ValueError(f"{sub.name}: Present classes ({sub.present}) cannot exceed total conducted ({sub.total}).")

    subject_names = {s.name.strip() for s in payload.subjects if s.name.strip()}
    no_class_set = set(payload.no_class_dates)

    future_start = payload.future_start_date or payload.start_date
    if future_start < payload.start_date or future_start > payload.end_date:
        raise ValueError("Future-start date must be within the semester dates.")

    counts, last_dates, teaching_days = generate_datewise_schedule(
        start_date=future_start,
        end_date=payload.end_date,
        weekdays=payload.weekdays,
        no_class_dates=no_class_set,
        special_working_days=payload.special_working_days,
        subject_names=subject_names,
    )

    results: list[SubjectProjectionResult] = []
    warnings: list[str] = []

    for sub in payload.subjects:
        name = sub.name.strip()
        future = counts.get(name, 0)
        final_total = sub.total + future
        current_pct = (sub.present / sub.total * 100.0) if sub.total > 0 else 100.0
        projected_if_all = ((sub.present + future) / final_total * 100.0) if final_total > 0 else 100.0

        sub_warning = None
        if future == 0:
            sub_warning = f"No future periods scheduled for '{name}' between {payload.start_date} and {payload.end_date}."
            warnings.append(sub_warning)

        # Quick calc math applied per subject
        qc_result = calculate_quick_attendance(
            QuickCalculatorInput(
                present=sub.present,
                total=sub.total,
                future=future,
                target_percentage=payload.target_percentage,
            )
        )

        results.append(
            SubjectProjectionResult(
                name=name,
                present=sub.present,
                total=sub.total,
                current_percentage=round(current_pct, 2),
                future_classes=future,
                final_total_classes=final_total,
                projected_if_attend_all=round(projected_if_all, 2),
                classes_to_attend=qc_result.min_future_classes_to_attend,
                classes_can_skip=qc_result.max_future_classes_can_skip,
                achievable=qc_result.achievable,
                last_scheduled_class_date=last_dates.get(name),
                warning=sub_warning,
            )
        )

    return SemesterPlanResponse(
        target_percentage=payload.target_percentage,
        start_date=payload.start_date,
        end_date=payload.end_date,
        total_teaching_days=teaching_days,
        subjects=results,
        warnings=warnings,
    )
