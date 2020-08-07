import datetime

from assignment import Assignment
from typing import Dict, List

class AssignmentGrade:
    def __init__(self, assignment_name: str, score: float, lateness: datetime.timedelta) -> None:
        self.assignment_name = assignment_name
        self.score = score
        self.lateness = lateness

    def __repr__(self) -> str:
        return "AssignmentGrade('{}', {}, {})".format(self.assignment_name, self.score, repr(self.lateness))

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
                total_grade += assignment_score * assignment.weight
            return total_grade
        total_grade_possibities = map(get_grade_possibility, self.grade_possibilities)
        total_grade = max(total_grade_possibities)
        return total_grade
