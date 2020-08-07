import datetime

from assignment import Assignment
from typing import Dict, List

class Multiplier:
    def __init__(self, multiplier: float, description: str) -> None:
        assert multiplier >= 0.0, "Multiplier cannot be negative"
        self.multiplier = multiplier
        self.description = description

    def __repr__(self) -> str:
        return "Multiplier({}, '{}')".format(self.multiplier, self.description)

class AssignmentGrade:
    def __init__(self, assignment_name: str, score: float, lateness: datetime.timedelta, slip_days_applied: int = 0, multipliers_applied: List[Multiplier] = None) -> None:
        self.assignment_name = assignment_name
        self.score = score
        self.lateness = lateness
        self.slip_days_applied = slip_days_applied
        self.multipliers_applied: List[Multiplier] = multipliers_applied if multipliers_applied else []

    def __repr__(self) -> str:
        return "AssignmentGrade('{}', {}, {}, {}, {})".format(self.assignment_name, self.score, repr(self.lateness), self.slip_days_applied, self.multipliers_applied)

class Student:
    def __init__(self, sid: int, name: str, grade_possibilities: List[Dict[str, AssignmentGrade]] = None) -> None:
        self.sid = sid
        self.name = name
        self.grade_possibilities: List[Dict[str, AssignmentGrade]] = [] if not grade_possibilities else grade_possibilities

    def __repr__(self) -> str:
        return "Student({}, '{}', {})".format(self.sid, self.name, self.grade_possibilities)

    def get_grade(self, assignments: Dict[str, Assignment]) -> float:
        def get_grade_possibility(grade_possibility: Dict[str, AssignmentGrade]):
            total_grade = 0.0
            for grade in grade_possibility.values():
                assert grade.assignment_name in assignments, "Graded assignment entry not in assignments"
                assignment = assignments[grade.assignment_name]
                assignment_score = grade.score / assignment.score_possible
                for multiplier in grade.multipliers_applied:
                    assignment_score *= multiplier.multiplier
                total_grade += assignment_score * assignment.weight
            return total_grade
        total_grade_possibities = map(get_grade_possibility, self.grade_possibilities)
        total_grade = max(total_grade_possibities)
        return total_grade
