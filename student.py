import datetime

from assignment import Assignment
from category import Category
from typing import Dict, List, Tuple

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

class GradeReport:
    def __init__(self, total_grade: float = 0.0, categories: Dict[str, Tuple[float, float]] = None, assignments: Dict[str, Tuple[float, float, float, str]] = None) -> None:
        self.total_grade = total_grade
        # Tuple is raw, weighted, comment
        self.categories: Dict[str, Tuple[float, float]] = categories if categories else {}
        # Tuple is raw, category-weighted, weighted, comment
        self.assignments: Dict[str, Tuple[float, float, float, str]] = assignments if assignments else {}

    @classmethod
    def from_possibility(cls, grade_possibility: Dict[str, AssignmentGrade], assignments: Dict[str, Assignment], categories: Dict[str, Category]):
        grade_report = GradeReport()
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
            category_weighted_grade = category_grade * category.weight
            grade_report.categories[category.name] = (category_grade, category_weighted_grade)
            grade_report.total_grade += category_weighted_grade
        return grade_report

    def __repr__(self) -> str:
        return "GradeReport({}, {}, {})".format(self.total_grade, self.categories, self.assignments)

class Student:
    def __init__(self, sid: int, name: str, grade_possibilities: List[Dict[str, AssignmentGrade]] = None) -> None:
        self.sid = sid
        self.name = name
        self.grade_possibilities: List[Dict[str, AssignmentGrade]] = [] if not grade_possibilities else grade_possibilities

    def __repr__(self) -> str:
        return "Student({}, '{}', {})".format(self.sid, self.name, self.grade_possibilities)

    def get_grade_report(self, assignments: Dict[str, Assignment], categories: Dict[str, Category]) -> GradeReport:
        best_grade_report: GradeReport = GradeReport()
        best_grade_report.total_grade = -float('inf')
        for grade_possibility in self.grade_possibilities:
            grade_report = GradeReport.from_possibility(grade_possibility, assignments, categories)
            if grade_report.total_grade > best_grade_report.total_grade:
                best_grade_report = grade_report
        return best_grade_report
