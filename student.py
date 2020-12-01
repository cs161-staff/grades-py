import datetime
import enum
import statistics

from typing import Dict, List, Optional, Tuple

class Multiplier:
    def __init__(self, multiplier: float, description: str) -> None:
        assert multiplier >= 0.0, 'Multiplier cannot be negative'
        self.multiplier = multiplier
        self.description = description

    def __repr__(self) -> str:
        return f'Multiplier({self.multiplier}, {self.description})'

class Category:
    def __init__(self, name: str, weight: float, drops: int, slip_days: int, has_late_multiplier: bool = False, override: Optional[float] = None, comments: List[str] = None) -> None:
        self.name = name
        self.weight = weight
        self.drops = drops
        self.slip_days = slip_days
        self.has_late_multiplier = has_late_multiplier
        self.override = override
        self.comments = comments if comments is not None else []

    def __repr__(self) -> str:
        return f'Category({self.name}, {self.weight}, {self.drops}, {self.slip_days}, {self.has_late_multiplier}, {self.override}, {self.comments})'

class Assignment:
    class Grade:
        def __init__(self, score: float, lateness: datetime.timedelta, multipliers_applied: List[Multiplier] = None, dropped: bool = False, override: Optional[float] = None, comments: List[str] = None) -> None:
            self.score = score
            self.lateness = lateness
            self.multipliers_applied = multipliers_applied if multipliers_applied is not None else []
            self.dropped = dropped
            self.override = override
            self.comments = comments if comments is not None else []

        def get_score(self) -> float:
            score = self.score if self.override is None else self.override
            for multiplier in self.multipliers_applied:
                score *= multiplier.multiplier
            return score

        def __repr__(self) -> str:
            return f'AssignmentGrade({self.score}, {self.lateness}, {self.multipliers_applied}, {self.dropped}, {self.override}, {self.comments})'

    def __init__(self, name: str, category: str, score_possible: float, weight: float, slip_group: int, grade: Optional['Assignment.Grade'] = None) -> None:
        self.name = name
        self.category = category
        self.score_possible = score_possible
        self.weight = weight
        self.slip_group = slip_group
        self._grade = grade

    @property
    def grade(self) -> 'Assignment.Grade':
        assert self._grade is not None, 'Grade is not yet initialized'
        return self._grade

    @grade.setter
    def grade(self, grade: 'Assignment.Grade') -> None:
        self._grade = grade

    def __repr__(self) -> str:
        return f'Assignment({self.name}, {self.category}, {self.score_possible}, {self.weight}, {self.slip_group}, {self._grade})'

class GradeReport:
    class CategoryEntry:
        def __init__(self, raw: float, adjusted: float, weighted: float, comments: List[str]) -> None:
            self.raw = raw
            self.adjusted = adjusted
            self.weighted = weighted
            self.comments = comments

        def __repr__(self) -> str:
            return f'GradeReport.CategoryEntry({self.raw}, {self.adjusted}, {self.weighted}, {self.comments})'

    class AssignmentEntry:
        def __init__(self, raw: float, adjusted: float, weighted: float, comments: List[str]) -> None:
            self.raw = raw
            self.adjusted = adjusted
            self.weighted = weighted
            self.comments = comments

        def __repr__(self) -> str:
            return f'GradeReport.AssignmentEntry({self.raw}, {self.adjusted}, {self.weighted}, {self.comments})'

    def __init__(self, sid: int, student_name: str, total_grade: float = 0.0, categories: Dict[str, 'GradeReport.CategoryEntry'] = None, assignments: Dict[str, 'GradeReport.AssignmentEntry'] = None) -> None:
        self.sid = sid
        self.student_name = student_name
        self.total_grade = total_grade
        self.categories = categories if categories is not None else {}
        self.assignments = assignments if assignments is not None else {}

    def __repr__(self) -> str:
        return f'GradeReport({self.sid}, {self.student_name}, {self.total_grade}, {self.categories}, {self.assignments})'

class Student:
    def __init__(self, sid: int, name: str, categories: Dict[str, Category], assignments: Dict[str, Assignment]) -> None:
        self.sid = sid
        self.name = name
        self.categories = categories
        self.assignments = assignments

    def __repr__(self) -> str:
        return f'Student({self.sid}, {self.name}, {self.categories}, {self.assignments})'

    def get_grade_report(self) -> GradeReport:
        grade_report = GradeReport(self.sid, self.name)
        for category in self.categories.values():
            assignments_in_category = list(assignment for assignment in self.assignments.values() if assignment.category == category.name)
            category_numerator = 0.0 # Category-weighted grades on assignments
            category_denominator = 0.0 # Total assignment weights

            # Category denominator.
            for assignment in assignments_in_category:
                grade = self.assignments[assignment.name].grade
                if not grade.dropped:
                    category_denominator += assignment.weight

            # AssignmentEntry objects with multipliers for adjusted score, weighted score, and cateogry numerator.
            for assignment in assignments_in_category:
                grade = self.assignments[assignment.name].grade
                assignment_raw_grade = grade.score / assignment.score_possible
                assignment_adjusted_grade = grade.get_score() / assignment.score_possible
                if not grade.dropped:
                    category_numerator += assignment_adjusted_grade * assignment.weight
                    assignment_weighted_grade = assignment_adjusted_grade / category_denominator * assignment.weight * category.weight
                else:
                    assignment_weighted_grade = 0.0
                assignment_comments = list(grade.comments)
                for multiplier in grade.multipliers_applied:
                    assignment_comments.append(f'x{multiplier.multiplier} ({multiplier.description})')
                grade_report.assignments[assignment.name] = GradeReport.AssignmentEntry(assignment_raw_grade, assignment_adjusted_grade, assignment_weighted_grade, assignment_comments)

            # CategoryEntry.
            category_raw_grade = category_numerator / category_denominator if category_denominator > 0.0 else 0.0
            if category.override is not None:
                category_adjusted_grade = category.override
            else:
                category_adjusted_grade = category_raw_grade
            category_weighted_grade = category_adjusted_grade * category.weight
            category_comments = list(category.comments)
            grade_report.categories[category.name] = GradeReport.CategoryEntry(category_raw_grade, category_adjusted_grade, category_weighted_grade, category_comments)

            # Add to total grade.
            grade_report.total_grade += category_weighted_grade

        return grade_report
