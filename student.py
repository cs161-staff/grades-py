import datetime
import enum

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

    def get_new_score(self, target: str, student: 'Student') -> float:
        if self.clobber_type == Clobber.Type.ABSOLUTE:
            score = student.assignments[self.source].grade.get_score()
        elif self.clobber_type == Clobber.Type.SCALED:
            score = student.assignments[self.source].grade.get_score()
            score /= student.assignments[self.source].score_possible
            score *= student.assignments[target].score_possible
        else:
            raise RuntimeError(f'Unknown clobber type {self.clobber_type}')

        score *= self.scale

        return score

    def __repr__(self) -> str:
        return f'Clobber({self.clobber_type}, {self.source}, {self.scale})'

class Category:
    def __init__(self, name: str, weight: float, drops: int, slip_days: int, has_late_multiplier: bool = False) -> None:
        self.name = name
        self.weight = weight
        self.drops = drops
        self.slip_days = slip_days
        self.has_late_multiplier = has_late_multiplier

    def __repr__(self) -> str:
        return f'Category({self.name}, {self.weight}, {self.drops}, {self.slip_days}, {self.has_late_multiplier})'

class Assignment:
    class Grade:
        def __init__(self, score: float, lateness: datetime.timedelta, multipliers_applied: List[Multiplier] = None, dropped: bool = False, comments: List[str] = None, clobber: Optional[Clobber] = None) -> None:
            self.score = score
            self.lateness = lateness
            self.multipliers_applied = multipliers_applied if multipliers_applied is not None else []
            self.dropped = dropped
            self.clobber = clobber
            self.comments = comments if comments is not None else []

        def get_score(self) -> float:
            score = self.score
            for multiplier in self.multipliers_applied:
                score *= multiplier.multiplier
            return score

        def __repr__(self) -> str:
            return f'AssignmentGrade({self.score}, {self.lateness}, {self.multipliers_applied}, {self.dropped}, {self.comments})'

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
        self.categories = categories if categories is not None else {}
        self.assignments = assignments if assignments is not None else {}

    def __repr__(self) -> str:
        return f'GradeReport({self.total_grade}, {self.categories}, {self.assignments})'

class Student:
    def __init__(self, sid: int, name: str, categories: Dict[str, Category], assignments: Dict[str, Assignment]) -> None:
        self.sid = sid
        self.name = name
        self.categories = categories
        self.assignments = assignments

    def __repr__(self) -> str:
        return f'Student({self.sid}, {self.name}, {self.categories}, {self.assignments})'

    def get_grade_report(self) -> GradeReport:
        grade_report = GradeReport()
        for category in self.categories.values():
            assignments_in_category = list(assignment for assignment in self.assignments.values() if assignment.category == category.name)
            category_numerator = 0.0 # Category-weighted grades on assignments
            category_denominator = 0.0 # Total assignment weights

            # Compute category denominator.
            for assignment in assignments_in_category:
                grade = self.assignments[assignment.name].grade
                if not grade.dropped:
                    category_denominator += assignment.weight

            # Create AssignmentEntry objects with multipliers for adjusted score.
            for assignment in assignments_in_category:
                grade = self.assignments[assignment.name].grade
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
                grade = self.assignments[assignment.name].grade
                assignment_entry = grade_report.assignments[assignment.name]

                # Clobbers.
                if grade.clobber is not None:
                    new_adjusted_score = grade.clobber.get_new_score(assignment.name, self)
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
