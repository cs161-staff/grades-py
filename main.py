import argparse
import copy
import csv
import datetime
import sys
from typing import Any, Dict, List, Set, Tuple

from assignment import Assignment
from category import Category
from student import AssignmentGrade, Multiplier, Student

def import_roster(path: str) -> Dict[int, Student]:
    """Imports the CalCentral roster in the CSV file at the given path

    :param path: The path of the CalCentral roster
    :type path: str
    :returns: A dict mapping student IDs to students
    :rtype: dict
    """
    students: Dict[int, Student] = {}
    with open(path) as roster_file:
        reader = csv.DictReader(roster_file)
        for row in reader:
            sid = int(row["Student ID"])
            name = row["Name"]
            students[sid] = Student(sid, name)
    return students

def import_categories(path: str, students: Dict[int, Student]) -> Dict[str, Category]:
    """Imports assignment categories the CSV file at the given path and initializes students' slip day and drop values

    :param path: The path of the category CSV
    :type path: str
    :returns: A dict mapping category names to categories
    :rtype: dict
    """
    categories: Dict[str, Category] = {}
    with open(path) as roster_file:
        reader = csv.DictReader(roster_file)
        for row in reader:
            name = row["Name"]
            weight = float(row["Weight"])
            has_late_multiplier = bool(int(row["Has Late Multiplier"]))
            categories[name] = Category(name, weight, has_late_multiplier)

            drops = int(row["Drops"])
            slip_days = int(row["Slip Days"])
            for student in students.values():
                student.drops[name] = drops
                student.slip_days[name] = slip_days

    return categories

def import_assignments(path: str, categories: Dict[str, Category]) -> Dict[str, Assignment]:
    """Imports assignments from the CSV file at the given path

    :param path: The path of the assignments CSV
    :type path: str
    :param categories: The categories for assignments
    :type categories: dict
    :returns: A dict mapping assignment names to assignments
    :rtype: dict
    """
    assignments: Dict[str, Assignment] = {}
    with open(path) as assignment_file:
        reader = csv.DictReader(assignment_file)
        for row in reader:
            name = row["Name"]
            category = row["Category"]
            score_possible = float(row["Possible"])
            weight = float(row["Weight"])
            slip_group_str = row["Slip Group"]
            if slip_group_str == None or slip_group_str == "":
                slip_group = -1
            else:
                slip_group = int(slip_group_str)
            if category not in categories:
                raise RuntimeError("Assignment {} references unknown category {}".format(name, category))
            assignments[name] = Assignment(name, category, score_possible, weight, slip_group)
    return assignments

def import_grades(path: str, students: Dict[int, Student], assignments: Dict[str, Assignment]) -> None:
    """Imports the Gradescope grade rports in the CSV file at the given path and imports them into the students

    :param path: The path of the Gradescope grade rport
    :type path: str
    :param students: The students into which grades will be entered
    :type students: dict
    :param assignments: The assignments
    :type assignments: dict
    :param students: The students from `import_roster`
    :type students: list
    """
    with open(path) as grades_file:
        reader = csv.DictReader(grades_file)
        for row in reader:
            try:
                sid = int(row["SID"])
            except ValueError as e:
                continue
            if sid not in students:
                # Skip students not in roster
                continue

            student = students[sid]

            grades: Dict[str, AssignmentGrade] = {}
            for assignment_name in assignments:
                assignment_lateness_header = "{} - Lateness (H:M:S)".format(assignment_name)
                assignment_max_points_header = "{} - Max Points".format(assignment_name)

                score: float
                if assignment_name in row:
                    scorestr = row[assignment_name]
                    if scorestr != "":
                        score = float(scorestr)
                        # Lateness formatted as HH:MM:SS
                        lateness_components = row[assignment_lateness_header].split(":")
                        hours = int(lateness_components[0])
                        minutes = int(lateness_components[1])
                        seconds = int(lateness_components[2])
                        lateness = datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)

                        # Take min with max score possible on Gradescope
                        max_score = float(row[assignment_max_points_header])
                        score = min(max_score, score)
                    else:
                        # Empty string score string means no submission; assume 0.0
                        score = 0.0
                        lateness = datetime.timedelta(0)
                else:
                    # No column for assignment; assume 0.0
                    score = 0.0
                    lateness = datetime.timedelta(0)

                grade = AssignmentGrade(assignment_name, score, lateness)
                grades[assignment_name] = grade

            # Upon importing, there is only one possibility so far
            student.grade_possibilities = [grades]

def apply_accommodations(acccomodations_path: str, students: Dict[int, Student]) -> None:
    with open(acccomodations_path) as accommodations_file:
        reader = csv.DictReader(accommodations_file)
        for row in reader:
            sid = int(row["SID"])
            category = row["Category"]
            drop_adjust = int(row["Drop Adjust"])
            slip_day_adjust = int(row["Slip Day Adjust"])

            if sid not in students:
                # Don't raise an error because students may drop from roster
                continue

            student = students[sid]

            if category not in student.drops or category not in student.slip_days:
                # If not present in student.drops or student.slip_days, it wasn't present in categories CSV
                raise RuntimeError("Accommodations reference nonexistent category {}".format(category))

            student.drops[category] += drop_adjust
            student.slip_days[category] += slip_day_adjust

def apply_extensions(path: str, students: Dict[int, Student]) -> None:
    """Imports and applies the extensions in the CSV file at the given path to the students

    :param path: The path of the extensions CSV
    :type path: str
    :param students: The students to whom to apply the extensions
    :type students: dict
    """
    with open(path) as extensions_file:
        reader = csv.DictReader(extensions_file)
        for row in reader:
            sid = int(row["SID"])
            assignment_name = row["Assignment"]
            days = int(row["Days"])

            if sid not in students:
                # Don't raise an error because students may drop from roster
                continue

            student = students[sid]
            zero = datetime.timedelta(0)

            for grade_possibility in student.grade_possibilities:
                if assignment_name not in grade_possibility:
                    # If not present in grade_possibility, it wasn't present in assignments CSV
                    raise RuntimeError("Extension references unknown assignment {}".format(assignment_name))
                grade = grade_possibility[assignment_name]
                grade.lateness = max(grade.lateness - datetime.timedelta(days=days), zero)

def apply_slip_days(students: Dict[int, Student], assignments: Dict[str, Assignment], categories: Dict[str, Category]) -> None:
    """Applies slip days per category to students

    Slip days are applied using a brute-force method of enumerating all possible ways to assign slip days to assignments. The appropriate lateness is removed from the grade entry.

    :param students: The students to whom to apply slip days
    :type students: dict
    :param assignments: The assignments
    :type assignments: dict
    :param categories: The assignment categories, containing numbers of slip days
    :type categories: dict
    """
    def get_slip_possibilities(num_assignments: int, slip_days: int) -> List[List[int]]:
        # Basically np.meshgrid with max sum <= slip_days
        # TODO Optimize by removing unnecessary slip day possiblities (e.g. only using 2 when you can use 3)
        if num_assignments == 0:
            return [[]]
        possibilities: List[List[int]] = []
        for i in range(slip_days + 1):
            # i is the number of slip days used for the first assignment
            rest = get_slip_possibilities(num_assignments - 1, slip_days - i)
            rest = list(map(lambda possibility: [i] + possibility, rest))
            possibilities.extend(rest)
        return possibilities

    zero = datetime.timedelta(0)

    for category in categories.values():
        assignments_in_category = list(filter(lambda a: a.category == category.name, assignments.values()))
        for student in students.values():
            # Shallow copy student.grade_possibilities for concurrent modification
            for old_grade_possibility in list(student.grade_possibilities):
                late_slip_groups: Set[int] = set()
                for grade in old_grade_possibility.values():
                    assignment = assignments[grade.assignment_name]
                    if grade.lateness > zero and assignment.slip_group != -1:
                        late_slip_groups.add(assignments[grade.assignment_name].slip_group)
                slip_possibilities = get_slip_possibilities(len(late_slip_groups), student.slip_days[category.name])
                late_slip_groups_list = list(late_slip_groups)
                for slip_possibility in slip_possibilities:
                    if sum(slip_possibility) == 0:
                        # Skip 0 case, which is already present
                        continue
                    possibility_with_slip = copy.deepcopy(old_grade_possibility)
                    for i in range(len(late_slip_groups_list)):
                        slip_group = late_slip_groups_list[i]
                        slip_days = slip_possibility[i]
                        for grade in possibility_with_slip.values():
                            grade_with_slip = possibility_with_slip[grade.assignment_name]
                            if assignments[grade.assignment_name].slip_group == slip_group:
                                grade_with_slip.slip_days_applied = slip_days
                                grade_with_slip.lateness = max(grade_with_slip.lateness - datetime.timedelta(days=slip_days), zero)
                    student.grade_possibilities.append(possibility_with_slip)

# TODO Put this in a config or something
LATE_MULTIPLIER_DESC = "Late multiplier"
LATE_MULTIPLIERS = [0.9, 0.8, 0.6]

def apply_late_multiplier(students: Dict[int, Student], assignments: Dict[str, Assignment], categories: Dict[str, Category]) -> None:
    """Applies late multipliers to students

    Late multipliers are applied by mutating every grade possibility and appending each grade's multipliers list.

    :param students: The students to whom to apply late multipliers
    :type students: dict
    :param assignments: The assignments
    :type assignments: dict
    :param categories: The assignment categories, containing numbers of drops
    :type categories: dict
    """
    def get_days_late(grade: AssignmentGrade) -> int:
        lateness = grade.lateness
        lateness -= datetime.timedelta(days=grade.slip_days_applied)
        lateness = max(zero, lateness)
        days_late = lateness.days
        if lateness % one > zero:
            days_late += 1
        return days_late

    zero = datetime.timedelta(0)
    one = datetime.timedelta(days=1)
    for student in students.values():
        for grade_possibility in student.grade_possibilities:
            for grade in grade_possibility.values():
                assignment = assignments[grade.assignment_name]
                category = categories[assignment.category]

                days_late = get_days_late(grade)

                late_multipliers: List[float]
                if category.has_late_multiplier:
                    late_multipliers = LATE_MULTIPLIERS
                else:
                    # Empty array means immediately 0.0 upon late
                    late_multipliers = []

                if days_late > 0:
                    if days_late <= len(late_multipliers): # <= because zero-indexing
                        multiplier = late_multipliers[days_late - 1] # + 1 because zero-indexing
                    else:
                        # Student submitted past latest possible time
                        multiplier = 0.0
                    grade.multipliers_applied.append(Multiplier(multiplier, LATE_MULTIPLIER_DESC))

def apply_drops(students: Dict[int, Student], assignments: Dict[str, Assignment], categories: Dict[str, Category]) -> None:
    """Applies drops per categories to students

    Drops are applied by setting the dropped variable for the lowest assignments in each category.

    :param students: The students to whom to apply late multipliers
    :type students: dict
    :param assignments: The assignments
    :type assignments: dict
    :param categories: The assignment categories, containing numbers of drops
    :type categories: dict
    """
    for category in categories.values():
        assignments_in_category = list(filter(lambda assignment: assignment.category == category.name, assignments.values()))
        assignment_names = list(map(lambda assignment: assignment.name, assignments_in_category))
        for student in students.values():
            for grade_possibility in student.grade_possibilities:
                grades = list(grade_possibility.values())
                grades = list(filter(lambda grade: grade.assignment_name in assignment_names, grades))
                grades.sort(key=lambda grade: grade.get_score() / assignments[grade.assignment_name].score_possible)
                drops = student.drops[category.name]
                grades_to_drop = grades[:drops]
                for grade_to_drop in grades_to_drop:
                    grade_to_drop.dropped = True

def dump_students(students: Dict[int, Student], assignments: Dict[str, Assignment], categories: Dict[str, Category]) -> None:
    """Dumps students as a CSV to stdout

    :param students: The students to dump
    :type students: dict
    :param assignments: The assignments
    :type assignments: dict
    """
    header = ["SID", "Name", "Total Score"]
    for category in categories.values():
        header.append("Category: {} - Score".format(category.name))
        header.append("Category: {} - Weighted Score".format(category.name))
    for assignment in assignments.values():
        header.append("{} - Raw Score".format(assignment.name))
        header.append("{} - Adjusted Score".format(assignment.name))
        header.append("{} - Weighted Score".format(assignment.name))
        header.append("{} - Comments".format(assignment.name))
    rows = [header]
    for student in students.values():
        grade_report = student.get_grade_report(assignments, categories)
        row: List[Any] = [student.sid, student.name, grade_report.total_grade]
        absent_category = ('no grades found', 'no grades found')
        absent_assignment = ('no grades found', 'no grades found', 'no grades found', 'no grades found')
        for category in categories.values():
            category_report: Tuple = grade_report.categories.get(category.name, absent_category)
            row.extend(category_report)
        for assignment in assignments.values():
            assignment_report: Tuple = grade_report.assignments.get(assignment.name, absent_assignment)
            row.extend(assignment_report)
        rows.append(row)
    csv.writer(sys.stdout).writerows(rows)

def main(args) -> None:
    roster_path = args.roster
    categories_path = args.categories
    assignments_path = args.assignments
    grades_path = args.grades
    extensions_path = args.extensions
    accomodations_path = args.accommodations

    students = import_roster(roster_path)
    categories = import_categories(categories_path, students)
    assignments = import_assignments(assignments_path, categories)

    import_grades(grades_path, students, assignments)
    apply_accommodations(accomodations_path, students)
    apply_extensions(extensions_path, students)
    apply_slip_days(students, assignments, categories)
    apply_late_multiplier(students, assignments, categories)
    apply_drops(students, assignments, categories)

    dump_students(students, assignments, categories)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("roster", help="csv roster downloaded from CalCentral")
    parser.add_argument("categories", help="csv grades with assignment categories")
    parser.add_argument("assignments", help="csv with assignments")
    parser.add_argument("grades", help="csv grades from Gradescope")
    parser.add_argument("extensions", help="csv grades with extensions")
    parser.add_argument("accommodations", help="csv grades with accommodations for drops and slip days")
    #parser.add_argument("output_path", help="path where csv output should be saved")
    parser.add_argument("--config", "--c", help="yaml file of configs")
    parser.add_argument("--bins", "--b", help="yaml with letter grade bins")
    parser.add_argument("--accommodations", "--a", help="accommdations, if any. Accommodations should be a csv file with at least 3 columns: SID, Assignment, Days. An additional \"Clobbered by\" column should be present for clobbers")
    parser.add_argument("--round", "--r", type=int, default=5, help="Number of decimal places to round to")
    parser.add_argument("--histogram", "--h", help="path where histogram, if desired, should be saved")
    parser.add_argument("-v", "--verbose", action="count", help="verbosity")
    args = parser.parse_args()
    main(args)
