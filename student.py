import datetime
import enum

from assignment import Assignment
from category import Category
from typing import Dict, List, Optional, Tuple

class Multiplier:
    def __init__(self, multiplier: float, description: str) -> None:
        assert multiplier >= 0.0, 'Multiplier cannot be negative'
        self.multiplier = multiplier
        self.description = description

    def __repr__(self) -> str:
        return f'Multiplier({self.multiplier}, {self.description})'

class Clobber:
    class Type(enum.Enum):
        ABSOLUTE = 'ABSOLUTE'
        SCALED = 'SCALED'
        ZSCORE = 'ZSCORE'

    def __init__(self, clobber_type: 'Clobber.Type', source: str, scale: float):
        self.clobber_type = clobber_type
        self.source = source
        self.scale = scale

    def get_new_score(self, target: str, student: 'Student', categories: Dict[str, Category], assignments: Dict[str, Assignment]) -> float:
        if self.clobber_type == Clobber.Type.ABSOLUTE:
            score = student.grades[self.source].get_score()
        elif self.clobber_type == Clobber.Type.SCALED:
            score = student.grades[self.source].get_score()
            score /= assignments[self.source].score_possible
            score *= assignments[target].score_possible
        else:
            raise RuntimeError(f'Unknown clobber type {self.clobber_type}')

        score *= self.scale

        return score

    def __repr__(self) -> str:
        return f'Clobber({self.clobber_type}, {self.source}, {self.scale})'

class AssignmentGrade:
    def __init__(self, assignment_name: str, score: float, lateness: datetime.timedelta, multipliers_applied: List[Multiplier] = None, dropped: bool = False, comments: List[str] = None, clobber: Optional[Clobber] = None) -> None:
        self.assignment_name = assignment_name
        self.score = score
        self.lateness = lateness
        self.multipliers_applied: List[Multiplier] = multipliers_applied if multipliers_applied is not None else []
        self.dropped = dropped
        self.clobber = clobber
        self.comments: List[str] = comments if comments is not None else []

    def get_score(self) -> float:
        score = self.score
        for multiplier in self.multipliers_applied:
            score *= multiplier.multiplier
        return score

    def __repr__(self) -> str:
        return f'AssignmentGrade({self.assignment_name}, {self.score}, {self.lateness}, {self.multipliers_applied}, {self.dropped}, {self.comments})'

class GradeReport:
    class CategoryEntry:
        def __init__(self, raw: float, adjusted: float, weighted: float, comment: str) -> None:
            self.raw = raw
            self.adjusted = adjusted
            self.weighted = weighted
            self.comment = comment

        def __repr__(self) -> str:
            return f'GradeReport.CategoryEntry({self.raw}, {self.adjusted}, {self.weighted}, {self.comment})'

    class AssignmentEntry:
        def __init__(self, raw: float, adjusted: float, weighted: float, comment: str) -> None:
            self.raw = raw
            self.adjusted = adjusted
            self.weighted = weighted
            self.comment = comment

        def __repr__(self) -> str:
            return f'GradeReport.AssignmentEntry({self.raw}, {self.adjusted}, {self.weighted}, {self.comment})'

    def __init__(self, total_grade: float = 0.0, categories: Dict[str, 'GradeReport.CategoryEntry'] = None, assignments: Dict[str, 'GradeReport.AssignmentEntry'] = None) -> None:
        self.total_grade = total_grade
        self.categories: Dict[str, GradeReport.CategoryEntry] = categories if categories is not None else {}
        self.assignments: Dict[str, GradeReport.AssignmentEntry] = assignments if assignments is not None else {}

    def __repr__(self) -> str:
        return f'GradeReport({self.total_grade}, {self.categories}, {self.assignments})'

class Student:
    def __init__(self, sid: int, name: str, drops: Dict[str, int] = None, slip_days: Dict[str, int] = None, grades: Dict[str, AssignmentGrade] = None) -> None:
        self.sid = sid
        self.name = name
        self.drops: Dict[str, int] = drops if drops is not None else {}
        self.slip_days: Dict[str, int] = slip_days if slip_days is not None else {}
        self.grades: Dict[str, AssignmentGrade] = grades if grades is not None else {}

    def __repr__(self) -> str:
        return f'Student({self.sid}, {self.name}, {self.drops}, {self.slip_days}, {self.grades})'

    def get_grade_report(self, assignments: Dict[str, Assignment], categories: Dict[str, Category]) -> GradeReport:
        grade_report = GradeReport()
        for category in categories.values():
            assignments_in_category = list(filter(lambda assignment: assignment.category == category.name, assignments.values()))
            category_numerator = 0.0 # Category-weighted grades on assignments
            category_denominator = 0.0 # Total assignment weights

            # Compute category denominator.
            for assignment in assignments_in_category:
                grade = self.grades[assignment.name]
                if not grade.dropped:
                    category_denominator += assignment.weight

            # Create AssignmentEntry objects with multipliers for adjusted score.
            for assignment in assignments_in_category:
                grade = self.grades[assignment.name]
                assignment_raw_grade = grade.score / assignment.score_possible
                assignment_adjusted_grade = grade.get_score() / assignment.score_possible
                assignment_comments = list(grade.comments)
                for multiplier in grade.multipliers_applied:
                    assignment_comments.append(f'x{multiplier.multiplier} ({multiplier.description})')
                assignment_comment = ', '.join(assignment_comments)
                grade_report.assignments[assignment.name] = GradeReport.AssignmentEntry(assignment_raw_grade, assignment_adjusted_grade, 0.0, assignment_comment) # 0.0 weighted grade as placeholder.

            # Clobbers, category numerator, and weighted grades.
            new_assignment_entries: List[GradeReport.AssignmentEntry] = []
            for assignment in assignments_in_category:
                grade = self.grades[assignment.name]
                assignment_entry = grade_report.assignments[assignment.name]

                # Clobbers.
                if grade.clobber is not None:
                    new_adjusted_score = grade.clobber.get_new_score(grade.assignment_name, self, categories, assignments)
                    assignment_entry.adjusted = new_adjusted_score / assignment.score_possible

                # Category numerator and weighted grades.
                if not grade.dropped:
                    category_numerator += assignment_entry.adjusted * assignment.weight
                    assignment_entry.weighted = assignment_entry.adjusted / category_denominator * assignment.weight * category.weight
                else:
                    assignment_entry.weighted = 0.0

            category_raw_grade = category_numerator / category_denominator if category_denominator > 0.0 else 0.0
            category_adjusted_grade = category_raw_grade # TODO Clobbers.
            category_weighted_grade = category_adjusted_grade * category.weight
            category_comment = ''
            grade_report.total_grade += category_weighted_grade

            grade_report.categories[category.name] = GradeReport.CategoryEntry(category_raw_grade, category_adjusted_grade, category_weighted_grade, category_comment)
        return grade_report
