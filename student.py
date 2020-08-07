import datetime

from assignment import Assignment
from typing import Dict

class AssignmentGrade:
    def __init__(self, assignment_name: str, score: float, lateness: datetime.timedelta) -> None:
        self.assignment_name = assignment_name
        self.score = score
        self.lateness = lateness

    def __repr__(self) -> str:
        return "AssignmentGrade('{}', {}, {})".format(self.assignment_name, self.score, repr(self.lateness))

class Student:
    def __init__(self, sid: int, name: str, grades: Dict[str, AssignmentGrade] = None) -> None:
        self.sid = sid
        self.name = name
        self.grades: Dict[str, AssignmentGrade] = {} if not grades else grades

    def __repr__(self) -> str:
        return "Student({}, '{}', {})".format(self.sid, self.name, self.grades)

    def get_grade(self, assignments: Dict[str, Assignment]) -> float:
        total_grade = 0.0
        for grade in self.grades.values():
            assert grade.assignment_name in assignments, "Graded assignment entry not in assignments"
            assignment = assignments[grade.assignment_name]
            assignment_score = grade.score / assignment.score_possible
            total_grade += assignment_score * assignment.weight
        return total_grade
