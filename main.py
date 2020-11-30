import argparse
import copy
import csv
import datetime
import itertools
import sys
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from assignment import Assignment
from category import Category
from student import AssignmentGrade, Clobber, GradeReport, Multiplier, Student

def import_categories(path: str) -> Dict[str, Category]:
    """Imports assignment categories the CSV file at the given path and initializes students' slip day and drop values.

    :param path: The path of the category CSV.
    :type path: str
    :returns: A dict mapping category names to categories.
    :rtype: dict
    """
    categories: Dict[str, Category] = {}
    with open(path) as roster_file:
        reader = csv.DictReader(roster_file)
        for row in reader:
            name = row['Name']
            weight = float(row['Weight'])
            has_late_multiplier = bool(int(row['Has Late Multiplier']))
            drops = int(row['Drops'])
            slip_days = int(row['Slip Days'])
            categories[name] = Category(name, weight, drops, slip_days, has_late_multiplier)
    return categories

def import_assignments(path: str, categories: Dict[str, Category]) -> Dict[str, Assignment]:
    """Imports assignments from the CSV file at the given path.

    :param path: The path of the assignments CSV.
    :type path: str
    :param categories: The categories for assignments.
    :type categories: dict
    :returns: A dict mapping assignment names to assignments.
    :rtype: dict
    """
    assignments: Dict[str, Assignment] = {}
    with open(path) as assignment_file:
        reader = csv.DictReader(assignment_file)
        for row in reader:
            name = row['Name']
            category = row['Category']
            score_possible = float(row['Possible'])
            weight = float(row['Weight'])
            slip_group_str = row['Slip Group']
            if slip_group_str == None or slip_group_str == '':
                slip_group = -1
            else:
                slip_group = int(slip_group_str)
            if category not in categories:
                raise RuntimeError(f'Assignment {name} references unknown category {category}')
            assignments[name] = Assignment(name, category, score_possible, weight, slip_group)
    return assignments

def import_roster_and_grades(roster_path: str, grades_path: str, categories: Dict[str, Category], assignments: Dict[str, Assignment]) -> Dict[int, List[Student]]:
    """Imports the CalCentral roster in the CSV file at the given path and then initializes students with the grades present in the given Gradescope grade report.

    :param roster_path: The path of the CalCentral roster.
    :type roster_path: str
    :param grades_path: The path of the Gradescope grade report.
    :type grades_path: str
    :param categories: The categories to initialize the students with.
    :type categories: dict
    :param assignments: The assignments to initialize the students with.
    :type assignments: dict
    :returns: A dict mapping student IDs to a one-element list of students.
    :rtype: dict
    """
    students: Dict[int, List[Student]] = {}
    with open(roster_path) as roster_file:
        reader = csv.DictReader(roster_file)
        for row in reader:
            sid = int(row['Student ID'])
            name = row['Name']
            students[sid] = [Student(sid, name, categories, assignments)]
    with open(grades_path) as grades_file:
        reader = csv.DictReader(grades_file)
        for row in reader:
            try:
                sid = int(row['SID'])
            except ValueError as e:
                continue
            if sid not in students:
                # Skip students not in roster.
                continue

            grades: Dict[str, AssignmentGrade] = {}
            for assignment_name in assignments:
                assignment_lateness_header = f'{assignment_name} - Lateness (H:M:S)'
                assignment_max_points_header = f'{assignment_name} - Max Points'

                score: float
                if assignment_name in row:
                    scorestr = row[assignment_name]
                    if scorestr != '':
                        score = float(scorestr)
                        # Lateness formatted as HH:MM:SS.
                        lateness_components = row[assignment_lateness_header].split(':')
                        hours = int(lateness_components[0])
                        minutes = int(lateness_components[1])
                        seconds = int(lateness_components[2])
                        lateness = datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)

                        # Take min with max score possible on Gradescope.
                        max_score = float(row[assignment_max_points_header])
                        score = min(max_score, score)
                    else:
                        # Empty string score string means no submission; assume 0.0.
                        score = 0.0
                        lateness = datetime.timedelta(0)
                else:
                    # No column for assignment; assume 0.0.
                    score = 0.0
                    lateness = datetime.timedelta(0)

                grade = AssignmentGrade(assignment_name, score, lateness)
                grades[assignment_name] = grade

            # Mutate students to add fresh copies of their grades.
            for student in students[sid]:
                student.grades = copy.deepcopy(grades)
    return students

def apply_policy(policy: Callable[[Student], List[Student]], students: Dict[int, List[Student]]) -> None:
    for sid in students.keys():
        students[sid] = [new_student for student in students[sid] for new_student in policy(student)]
        assert len(students[sid]) > 0, 'Policy function returned an empty list'

def make_accommodations(path: str) -> Callable[[Student], List[Student]]:
    """Returns a policy function that applies the accommodations in the CSV at the given path.

    Accommodations are applied by mutating the student objects to adjust how many drops and slip days they have.

    :param path: The path of the accommodations CSV.
    :type path: str
    :returns: An accommodations policy function.
    :rtype: callable
    """
    accommodations: Dict[int, List[Dict[str, str]]] = {}
    with open(path) as accommodations_file:
        reader = csv.DictReader(accommodations_file)
        for row in reader:
            sid = int(row['SID'])
            accommodations.setdefault(sid, []).append(row)

    def apply(student: Student) -> List[Student]:
        if student.sid not in accommodations:
            return [student]
        new_student = copy.deepcopy(student)
        for row in accommodations[new_student.sid]:
            category = row['Category']
            drop_adjust = int(row['Drop Adjust'])
            slip_day_adjust = int(row['Slip Day Adjust'])
            if category not in student.categories:
                # If not present in student.categories, it wasn't present in categories CSV.
                raise RuntimeError(f'Accommodations reference nonexistent category {category}')
            new_student.categories[category].drops += drop_adjust
            new_student.categories[category].slip_days += slip_day_adjust
        return [new_student]
    return apply

def make_extensions(path: str) -> Callable[[Student], List[Student]]:
    """Returns a policy function that applies the extensions in the CSV file.

    :param path: The path of the extensions CSV.
    :type path: str
    :returns: An extensions policy function.
    :rtype: callable
    """
    extensions: Dict[int, List[Dict[str, str]]] = {}
    with open(path) as extensions_file:
        reader = csv.DictReader(extensions_file)
        for row in reader:
            sid = int(row['SID'])
            extensions.setdefault(sid, []).append(row)
    zero = datetime.timedelta(0)

    def apply(student: Student) -> List[Student]:
        if student.sid not in extensions:
            return [student]
        new_student = copy.deepcopy(student)
        for row in extensions[new_student.sid]:
            assignment_name = row['Assignment']
            days = int(row['Days'])
            if assignment_name not in student.grades:
                # If not present in grade_possibility, it wasn't present in assignments CSV.
                raise RuntimeError(f'Extension references unknown assignment {assignment_name}')
            grade = new_student.grades[assignment_name]
            grade.lateness = max(grade.lateness - datetime.timedelta(days=days), zero)
        return [new_student]
    return apply

def make_slip_days() -> Callable[[Student], List[Student]]:
    """Returns a policy function that Applies slip days per category.

    Slip days are applied using a brute-force method of enumerating all possible ways to assign slip days to assignments. The appropriate lateness is removed from the grade entry, and a comment is added.

    :returns: A slip days policy function.
    :rtype: callable
    """
    def get_slip_possibilities(num_assignments: int, slip_days: int) -> List[List[int]]:
        # Basically np.meshgrid with max sum <= slip_days.
        # TODO Optimize by removing unnecessary slip day possiblities (e.g. only using 2 when you can use 3).
        if num_assignments == 0:
            return [[]]
        possibilities: List[List[int]] = []
        for i in range(slip_days + 1):
            # i is the number of slip days used for the first assignment.
            rest = get_slip_possibilities(num_assignments - 1, slip_days - i)
            rest = [[i] + possibility for possibility in rest]
            possibilities.extend(rest)
        return possibilities

    zero = datetime.timedelta(0)

    def apply(student: Student) -> List[Student]:
        # slip_groups[i] have slip_possibilities[i].
        slip_groups: List[Set[int]] = []
        slip_possibilities: List[List[List[int]]] = []

        for category_name in student.categories:
            category = student.categories[category_name]
            # Get all slip groups that the student has late in the category.
            category_slip_groups: Set[int] = set()
            for grade in student.grades.values():
                assignment = student.assignments[grade.assignment_name]
                if assignment.category == category.name and assignment.slip_group != -1 and grade.lateness > zero:
                    category_slip_groups.add(student.assignments[grade.assignment_name].slip_group)

            # Get all possible ways of applying slip days.
            category_slip_possibilities = get_slip_possibilities(len(category_slip_groups), category.slip_days)

            slip_groups.append(category_slip_groups)
            slip_possibilities.append(category_slip_possibilities)

        new_students: List[Student] = [student]

        # All possibilities is the cross product of all possibilities in each category.
        for slip_possibility in itertools.product(*slip_possibilities):
            if sum(slip_days for category_slip_possibility in slip_possibility for slip_days in category_slip_possibility) == 0:
                # Skip 0 slip day application case since it is already present in the list.
                continue
            student_with_slip = copy.deepcopy(student)
            for category_index in range(len(slip_possibility)):
                category_slip_groups = slip_groups[category_index]
                category_slip_groups_list = list(category_slip_groups)
                category_slip_possibility = slip_possibility[category_index]
                for i in range(len(category_slip_groups_list)):
                    slip_group = category_slip_groups_list[i]
                    slip_days = category_slip_possibility[i]
                    for grade in student_with_slip.grades.values():
                        if student.assignments[grade.assignment_name].slip_group == slip_group:
                            grade.lateness = max(grade.lateness - datetime.timedelta(days=slip_days), zero)
                            grade.comments.append(f'{slip_days} slip days applied')
            new_students.append(student_with_slip)

        return new_students

    return apply

# TODO Put this in a config or something.
LATE_MULTIPLIER_DESC = 'Late multiplier'
LATE_MULTIPLIERS = [0.9, 0.8, 0.6]
LATE_GRACE = datetime.timedelta(minutes=5)

def make_late_multiplier() -> Callable[[Student], List[Student]]:
    """Returns a policy function that applies late multipliers.

    Late multipliers are applied by appending to each grade's multipliers list.

    :returns: A late multiplier policy function.
    :rtype: callable
    """
    zero = datetime.timedelta(0)
    one = datetime.timedelta(days=1)

    def get_days_late(lateness: datetime.timedelta) -> int:
        lateness = max(zero, lateness)
        days_late = lateness.days
        if lateness % one > LATE_GRACE:
            days_late += 1
        return days_late

    def apply(student: Student) -> List[Student]:
        new_student = copy.deepcopy(student)

        # Build dict mapping slip groups to maximal number of days late.
        slip_group_lateness: Dict[int, datetime.timedelta] = {}
        for grade in new_student.grades.values():
            assignment = student.assignments[grade.assignment_name]
            if grade.lateness > zero and assignment.slip_group != -1 and (assignment.slip_group not in slip_group_lateness or grade.lateness > slip_group_lateness[assignment.slip_group]):
                slip_group_lateness[assignment.slip_group] = grade.lateness

        # Apply lateness.
        for grade in new_student.grades.values():
            assignment = student.assignments[grade.assignment_name]
            category = student.categories[assignment.category]

            # Lateness is based on individual assignment if no slip group, else use early maximal value.
            days_late: int
            if assignment.slip_group in slip_group_lateness:
                days_late = get_days_late(slip_group_lateness[assignment.slip_group])
            else:
                days_late = get_days_late(grade.lateness)

            if days_late > 0:
                late_multipliers: List[float]
                if category.has_late_multiplier:
                    late_multipliers = LATE_MULTIPLIERS
                else:
                    # Empty array means immediately 0.0 upon late.
                    late_multipliers = []

                if days_late <= len(late_multipliers): # <= because zero-indexing.
                    multiplier = late_multipliers[days_late - 1] # + 1 because zero-indexing.
                else:
                    # Student submitted past latest possible time.
                    multiplier = 0.0
                grade.multipliers_applied.append(Multiplier(multiplier, LATE_MULTIPLIER_DESC))

        return [new_student]

    return apply

def make_clobbers(path: str) -> Callable[[Student], List[Student]]:
    category_clobbers: Dict[str, List[Clobber]] = {}
    assignment_clobbers: Dict[str, List[Clobber]] = {}
    with open(path) as clobbers_file:
        reader = csv.DictReader(clobbers_file)
        for row in reader:
            scope = row['Scope']
            target = row['Target']
            source = row['Source']
            scale = float(row['Scale'])
            clobber_type = Clobber.Type(row['Type'])
            clobber = Clobber(clobber_type, source, scale)
            if scope == 'CATEGORY':
                category_clobbers.setdefault(target, []).append(clobber)
            elif scope == 'ASSIGNMENT':
                assignment_clobbers.setdefault(target, []).append(clobber)
            else:
                raise RuntimeError(f'Unknown clobber scope {scope}')


    def apply(student: Student) -> List[Student]:
        # category_names[i] has possible clobbers category_possibilities[i].
        category_names = tuple(student.categories.keys())
        category_possibilities = tuple((None, *category_clobbers.get(name, [])) for name in category_names)
        # assignment_names[i] has possibe clobbers assignment_possibilities[i].
        assignment_names = tuple(student.assignments.keys())
        assignment_possibilities = tuple((None, *assignment_clobbers.get(name, [])) for name in assignment_names)

        # Compute all possibilities of applying clobbers.
        possibilities = tuple(itertools.product(itertools.product(*category_possibilities), itertools.product(*assignment_possibilities)))

        new_students = [student]
        for possibility in possibilities:
            if all(clobber is None for subpossibilities in possibility for clobber in subpossibilities):
                # Skip if all clobbers are None, since this is already part of the original student.
                continue
            category_possibility = possibility[0]
            assignment_possibility = possibility[1]
            new_student = copy.deepcopy(student)
            for category_index in range(len(category_names)):
                category_name = category_names[category_index]
                category_clobber = category_possibility[category_index]
                if category_clobber is not None:
                    raise NotImplementedError('Category clobbers not yet implemented')
            for assignment_index in range(len(assignment_names)):
                assignment_name = assignment_names[assignment_index]
                assignment_clobber = assignment_possibility[assignment_index]
                if assignment_clobber is not None:
                    new_student.grades[assignment_name].clobber = copy.deepcopy(assignment_clobber)
                    new_student.grades[assignment_name].comments.append(f'Clobbered by {clobber.source} using {clobber.clobber_type.value} at {clobber.scale} scale')
            new_students.append(new_student)
        return new_students
    return apply

def make_drops() -> Callable[[Student], List[Student]]:
    """Returns a policy function that applies drops per categories.

    Drops are applied by setting the dropped variable for all possible combinations of assignments to drop in each category.

    :returns: An assignment drop policy function.
    :rtype: callable
    """
    def apply(student: Student) -> List[Student]:
        # Assignments in drop_assignments[i] have drop_possibilities[i].
        drop_assignments: List[List[str]] = []
        drop_possibilities: List[Tuple[Tuple[bool, ...], ...]] = []

        for category in student.categories.values():
            # Get all ways to assign drops to assignments in the category.
            drops = student.categories[category.name].drops
            assignments_in_category = [assignment for assignment in student.assignments.values() if assignment.category == category.name]
            category_possibility = tuple(i < drops for i in range(len(assignments_in_category)))

            drop_assignments.append([assignment.name for assignment in assignments_in_category])
            drop_possibilities.append(tuple(sorted(set(itertools.permutations(category_possibility)))))

        new_students: List[Student] = []
        for drop_possibility in itertools.product(*drop_possibilities):
            new_student = copy.deepcopy(student)
            for category_index in range(len(drop_possibility)):
                category_possibility = drop_possibility[category_index]
                for assignment_index in range(len(category_possibility)):
                    assignment_name = drop_assignments[category_index][assignment_index]
                    should_drop = category_possibility[assignment_index]
                    if should_drop:
                        new_student.grades[assignment_name].dropped = True
                        new_student.grades[assignment_name].comments.append('Dropped')
            new_students.append(new_student)
        return new_students
    return apply

# TODO Put this in another CSV or something.
COMMENTS = {
    12345678: {
        'Midterm': ['Example comment 1', 'Example comment 2'],
    },
}

def make_comments(comments: Dict[int, Dict[str, List[str]]]) -> Callable[[Student], List[Student]]:
    """Returns a policy function that adds comments.

    :param comments: A dict mapping student IDs to a dict mapping assignment names to the list of comments.
    :type comments: dict
    :returns: A comments policy function.
    :rtype: callable
    """
    def apply(student: Student) -> List[Student]:
        if student.sid not in comments:
            return [student]
        new_student = copy.deepcopy(student)
        for assignment_name in comments[new_student.sid]:
            if assignment_name not in student.grades:
                # If not present in grade_possibility, it wasn't present in assignments CSV.
                raise RuntimeError(f'Comment references unknown assignment {assignment_name}')
            assignment_comments = comments[new_student.sid][assignment_name]
            new_student.grades[assignment_name].comments.extend(assignment_comments)
        return [new_student]
    return apply

def dump_students(students: Dict[int, List[Student]], assignments: Dict[str, Assignment], categories: Dict[str, Category], rounding: Optional[int] = None) -> None:
    """Dumps students as a CSV to stdout.

    :param students: The students to dump.
    :type students: dict
    :param assignments: The assignments.
    :type assignments: dict
    :param categories: The categories.
    :type categories: dict
    :param rounding: The number of decimal places to round to, or None if no rounding.
    :type rounding: int
    """
    grade_reports: Dict[int, GradeReport] = {}

    for sid in students:
        for student in students[sid]:
            grade_report = student.get_grade_report()
            if sid not in grade_reports or grade_report.total_grade > grade_reports[sid].total_grade:
                grade_reports[sid] = grade_report

    # Derive output rows.
    header = ['SID', 'Name', 'Total Score', 'Percentile']
    for category in categories.values():
        header.append(f'Category: {category.name} - Raw Score')
        header.append(f'Category: {category.name} - Adjusted Score')
        header.append(f'Category: {category.name} - Weighted Score')
        header.append(f'Category: {category.name} - Comments')
    for assignment in assignments.values():
        header.append(f'{assignment.name} - Raw Score')
        header.append(f'{assignment.name} - Adjusted Score')
        header.append(f'{assignment.name} - Weighted Score')
        header.append(f'{assignment.name} - Comments')
    rows: List[List[Any]] = [header]
    for sid in students:
        grade_report = grade_reports[sid]
        row: List[Any] = [student.sid, student.name, grade_report.total_grade, 0.0] # 0.0 is temporary percentile.
        absent = ('no grades found', 'no grades found', 'no grades found', 'no grades found')
        for category in categories.values():
            if category.name in grade_report.categories:
                category_report = grade_report.categories[category.name]
                row.append(category_report.raw)
                row.append(category_report.adjusted)
                row.append(category_report.weighted)
                row.append(category_report.comment)
            else:
                row.extend(absent)
        for assignment in assignments.values():
            if assignment.name in grade_report.assignments:
                assignment_report = grade_report.assignments[assignment.name]
                row.append(assignment_report.raw)
                row.append(assignment_report.adjusted)
                row.append(assignment_report.weighted)
                row.append(assignment_report.comment)
            else:
                row.extend(absent)
        rows.append(row)

    # Compute percentiles.
    students_by_score = list(students.keys())
    students_by_score.sort(key=lambda sid: grade_reports[sid].total_grade, reverse=True)
    num_students = len(students)
    student_percentiles: Dict[int, float] = {}
    for rank in range(len(students)):
        sid = students_by_score[rank]
        student_percentiles[sid] = 1.0 - rank / num_students
    for row in rows:
        if row is header:
            continue
        sid = row[0]
        row[3] = student_percentiles[sid]

    # Round rows.
    if rounding is not None:
        for row in rows:
            for i in range(len(row)):
                if isinstance(row[i], float):
                    row[i] = round(row[i], rounding)

    csv.writer(sys.stdout).writerows(rows)

def main(args: argparse.Namespace) -> None:
    roster_path = args.roster
    categories_path = args.categories
    assignments_path = args.assignments
    grades_path = args.grades
    clobbers_path = args.clobbers
    extensions_path = args.extensions
    accommodations_path = args.accommodations
    rounding = int(args.rounding) if args.rounding else None

    categories = import_categories(categories_path)
    assignments = import_assignments(assignments_path, categories)
    students = import_roster_and_grades(roster_path, grades_path, categories, assignments)

    if accommodations_path:
        apply_policy(make_accommodations(accommodations_path), students)
    if extensions_path:
        apply_policy(make_extensions(extensions_path), students)
    apply_policy(make_slip_days(), students)
    apply_policy(make_late_multiplier(), students)
    apply_policy(make_drops(), students)
    if clobbers_path:
        apply_policy(make_clobbers(clobbers_path), students)
    apply_policy(make_comments(COMMENTS), students)

    dump_students(students, assignments, categories, rounding)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('roster', help='CSV roster downloaded from CalCentral')
    parser.add_argument('grades', help='CSV grades downloaded from Gradescope')
    parser.add_argument('categories', help='CSV with assignment categories')
    parser.add_argument('assignments', help='CSV with assignments')
    parser.add_argument('--clobbers', '-c', help='CSV with clobbers')
    parser.add_argument('--extensions', '-e', help='CSV with extensions')
    parser.add_argument('--accommodations', '-a', help='CSV with accommodations for drops and slip days')
    parser.add_argument('--rounding', '-r', help='Number of decimal places to round to')
    #parser.add_argument('--config', '--c', help='yaml file of configs')
    #parser.add_argument('-v', '--verbose', action='count', help='verbosity')
    args = parser.parse_args()
    main(args)
