import datetime

from typing import Dict

class AssignmentGrade:
    def __init__(self, assignment_name: str, score: float, lateness: datetime.timedelta) -> None:
        self.assignment_name = assignment_name
        self.score = score
        self.lateness = lateness

    def __repr__(self) -> str:
        return "AssignmentGrade('{}', {}, {})".format(self.assignment_name, self.score, repr(self.lateness))

class Student:
    def __init__(self, sid: int, name: str, grades: Dict[str, AssignmentGrade] = {}) -> None:
        self.sid = sid
        self.name = name
        self.grades = grades

    def __repr__(self) -> str:
        return "Student({}, '{}', {})".format(self.sid, self.name, self.grades)
