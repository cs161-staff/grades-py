import datetime

from assignment import Assignment
from category import Category
from typing import Dict, List, Tuple

class Multiplier:
    def __init__(self, multiplier: float, description: str) -> None:
        assert multiplier >= 0.0, 'Multiplier cannot be negative'
        self.multiplier = multiplier
        self.description = description

    def __repr__(self) -> str:
        return f'Multiplier({self.multiplier}, {self.description})'

class AssignmentGrade:
    def __init__(self, assignment_name: str, score: float, lateness: datetime.timedelta, multipliers_applied: List[Multiplier] = None, dropped: bool = False, comments: List[str] = None) -> None:
        self.assignment_name = assignment_name
        self.score = score
        self.lateness = lateness
        self.multipliers_applied: List[Multiplier] = multipliers_applied if multipliers_applied else []
        self.dropped = dropped
        self.comments: List[str] = comments if comments else []

    def get_score(self) -> float:
        score = self.score
        for multiplier in self.multipliers_applied:
            score *= multiplier.multiplier
        return score

    def __repr__(self) -> str:
        return f'AssignmentGrade({self.assignment_name}, {self.score}, {self.lateness}, {self.multipliers_applied}, {self.dropped}, {self.comments})'

class GradeReport:
    def __init__(self, total_grade: float = 0.0, categories: Dict[str, Tuple[float, float]] = None, assignments: Dict[str, Tuple[float, float, float, str]] = None) -> None:
        self.total_grade = total_grade
        # Tuple is adjusted (with multipliers), weighted (contribution to course points)
        self.categories: Dict[str, Tuple[float, float]] = categories if categories else {}
        # Tuple is raw, adjusted (with multipliers), weighted (contribution to course points), comment
        self.assignments: Dict[str, Tuple[float, float, float, str]] = assignments if assignments else {}

    def __repr__(self) -> str:
        return f'GradeReport({self.total_grade}, {self.categories}, {self.assignments})'

class Student:
    def __init__(self, sid: int, name: str, drops: Dict[str, int] = {}, slip_days: Dict[str, int] = {}, grades: Dict[str, AssignmentGrade] = {}) -> None:
        self.sid = sid
        self.name = name
        self.drops = drops
        self.slip_days = slip_days
        self.grades: Dict[str, AssignmentGrade] = grades

    def __repr__(self) -> str:
        return f'Student({self.sid}, {self.name}, {self.drops}, {self.slip_days}, {self.grades})'

    def get_grade_report(self, assignments: Dict[str, Assignment], categories: Dict[str, Category]) -> GradeReport:
        grade_report = GradeReport()
        for category in categories.values():
            assignments_in_category = list(filter(lambda assignment: assignment.category == category.name, assignments.values()))
            category_numerator = 0.0 # Category-weighted grades on assignments
            category_denominator = 0.0 # Total assignment weights
            for assignment in assignments_in_category:
                grade = self.grades[assignment.name]
                assignment_adjusted_grade = grade.get_score()
                if not grade.dropped:
                    category_numerator += assignment_adjusted_grade / assignment.score_possible * assignment.weight
                    category_denominator += assignment.weight

            for assignment in assignments_in_category:
                grade = self.grades[assignment.name]
                assignment_raw_grade = grade.score / assignment.score_possible
                assignment_adjusted_grade = grade.get_score() / assignment.score_possible
                assignment_comments: List[str] = list(grade.comments)
                if grade.dropped:
                    assignment_weighted_grade = 0.0
                    assignment_comments.append('Dropped')
                else:
                    assignment_weighted_grade = assignment_adjusted_grade / category_denominator * assignment.weight * category.weight
                for multiplier in grade.multipliers_applied:
                    assignment_comments.append(f'x{multiplier.multiplier} ({multiplier.description})')
                assignment_comment = ', '.join(assignment_comments)
                grade_report.assignments[assignment.name] = (assignment_raw_grade, assignment_adjusted_grade, assignment_weighted_grade, assignment_comment)

            category_grade = category_numerator / category_denominator
            category_weighted_grade = category_grade * category.weight
            grade_report.total_grade += category_weighted_grade

            grade_report.categories[category.name] = (category_grade, category_weighted_grade)
        return grade_report
