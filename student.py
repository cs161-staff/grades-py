import datetime

from assignment import Assignment
from category import Category
from typing import Dict, List

class Multiplier:
    def __init__(self, multiplier: float, description: str) -> None:
        assert multiplier >= 0.0, "Multiplier cannot be negative"
        self.multiplier = multiplier
        self.description = description

    def __repr__(self) -> str:
        return "Multiplier({}, '{}')".format(self.multiplier, self.description)

class AssignmentGrade:
    def __init__(self, assignment_name: str, score: float, lateness: datetime.timedelta, slip_days_applied: int = 0, multipliers_applied: List[Multiplier] = None, dropped: bool = False) -> None:
        self.assignment_name = assignment_name
        self.score = score
        self.lateness = lateness
        self.slip_days_applied = slip_days_applied
        self.multipliers_applied: List[Multiplier] = multipliers_applied if multipliers_applied else []
        self.dropped = dropped

    def get_score(self) -> float:
        score = self.score
        for multiplier in self.multipliers_applied:
            score *= multiplier.multiplier
        return score

    def __repr__(self) -> str:
        return "AssignmentGrade('{}', {}, {}, {}, {}, {})".format(self.assignment_name, self.score, repr(self.lateness), self.slip_days_applied, self.multipliers_applied, self.dropped)

class Student:
    def __init__(self, sid: int, name: str, grade_possibilities: List[Dict[str, AssignmentGrade]] = None) -> None:
        self.sid = sid
        self.name = name
        self.grade_possibilities: List[Dict[str, AssignmentGrade]] = [] if not grade_possibilities else grade_possibilities

    def __repr__(self) -> str:
        return "Student({}, '{}', {})".format(self.sid, self.name, self.grade_possibilities)

    def get_grade(self, assignments: Dict[str, Assignment], categories: Dict[str, Category]) -> float:
        def get_grade_possibility(grade_possibility: Dict[str, AssignmentGrade]):
            total_grade = 0.0
            for category in categories.values():
                assignments_in_category = filter(lambda assignment: assignment.category == category.name, assignments.values())
                category_numerator = 0.0 # Weighted grades on assignments
                category_denominator = 0.0 # Total assignment weights
                for assignment in assignments_in_category:
                    grade = grade_possibility[assignment.name]
                    if grade.dropped:
                        # Ignore dropped grades
                        continue
                    category_numerator += grade.get_score() / assignment.score_possible * assignment.weight
                    category_denominator += assignment.weight
                category_grade = category_numerator / category_denominator
                total_grade += category_grade * category.weight
            return total_grade
        total_grade_possibities = map(get_grade_possibility, self.grade_possibilities)
        total_grade = max(total_grade_possibities)
        return total_grade
