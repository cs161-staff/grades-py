import datetime

from typing import Dict

class AssignmentGrade:
    def __init__(self, assignment_name: str, points: float, lateness: datetime.timedelta):
        self.assignment_name = assignment_name
        self.points = points
        self.lateness = lateness

class Student:
    def __init__(self, sid: int, name: str, grades: Dict[str, AssignmentGrade] = {}) -> None:
        self.sid = sid
        self.name = name
        self.grades = grades

    def __repr__(self) -> str:
        return "Student({}, \"{}\", {})".format(self.sid, self.name, self.grades)
