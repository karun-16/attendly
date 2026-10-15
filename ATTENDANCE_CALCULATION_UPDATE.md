# Attendance calculation update

- The semester start date remains the academic-period boundary.
- A separate “Count future classes from” date controls the projection window and defaults to tomorrow, because the current attendance inputs should reflect classes held through today.
- Future periods are counted only between that date and the semester last working day, excluding dates in the non-teaching/holiday list. Weekday mapping still determines which periods occur on each day; add explicit special working days when a weekend is officially instructional.
- Safe skips use the exact threshold: minimum future classes to attend = max(0, ceil(target_fraction * (classes_already_held + future_classes) - classes_present)); safe skips = future_classes - minimum future classes to attend, if achievable.
- The semester attendance target defaults to 75%; 60%, 65%, 80%, 85%, 90%, and a custom percentage are also available.
