# Attendance subject grouping

Theory and lab periods contribute to the same attendance subject:

- Web Technologies + Web Technologies Lab -> Web Technologies
- Machine Learning + Machine Learning Lab -> Machine Learning
- Artificial Intelligence + Artificial Intelligence Lab -> Artificial Intelligence

Each timetable period counts as one class. A two-period lab therefore contributes two classes to the corresponding combined subject. The frontend canonicalizes labels before creating attendance rows, and the backend uses the same canonical naming rule for projection calculations.
