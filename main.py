import argparse
import copy
import csv
import datetime
from typing import Dict, List

from assignment import Assignment
from category import Category
from extension import Extension
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

def import_categories(path: str) -> Dict[str, Category]:
    """Imports assignment categories the CSV file at the given path

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
            drops = int(row["Drops"])
            slip_days = int(row["Slip Days"])
            has_late_multiplier = bool(row["Has Late Multiplier"])
            categories[name] = Category(name, drops, slip_days, has_late_multiplier)
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
            if category not in categories:
                raise RuntimeError("Assignment {} references unknown category {}".format(name, category))
            assignments[name] = Assignment(name, category, score_possible, weight)
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

                if assignment_name not in row:
                    # No column for assignment
                    continue
                scorestr = row[assignment_name]
                if scorestr == "":
                    # Empty string score string means no submission
                    continue
                score = float(scorestr)
                # Lateness formatted as HH:MM:SS
                lateness_components = row[assignment_lateness_header].split(":")
                lateness = datetime.timedelta(hours=int(lateness_components[0]), minutes=int(lateness_components[1]), seconds= int(lateness_components[2]))

                grade = AssignmentGrade(assignment_name, score, lateness)
                grades[assignment_name] = grade

            # Upon importing, there is only one possibility so far
            student.grade_possibilities = [grades]

def import_extensions(path: str) -> List[Extension]:
    """Imports the CalCentral roster in the CSV file at the given path

    :param path: The path of the extensions CSV
    :type path: str
    :returns: A list of extensions
    :rtype: list
    """
    extensions = []
    with open(path) as extensions_file:
        reader = csv.DictReader(extensions_file)
        for row in reader:
            sid = int(row["SID"])
            assignment_name = row["Assignment"]
            days = int(row["Days"])

            extension = Extension(sid, assignment_name, datetime.timedelta(days=days))
            extensions.append(extension)
    return extensions

def apply_extensions(students: Dict[int, Student], extensions: List[Extension]) -> None:
    """Applies extensions to the students.

    Extensions are applied by subtracting the length of the extension from the student's lateness for the assignment. There is only one possibility: that extensions are applied.

    :param students: The students to whom to apply the extensions
    :type students: dict
    :param extensions: The extension to be applied
    :type extensions: list
    """
    for extension in extensions:
        if extension.sid not in students:
            # Skip students not in roster
            continue
        student = students[extension.sid]
        for grade_possibility in student.grade_possibilities:
            if extension.assignment_name not in grade_possibility:
                # Skip assignments not in assignments list
                # Assignment will not be in student.grades if not in assignment list
                return
            grade = grade_possibility[extension.assignment_name]
            grade.lateness = max(grade.lateness - extension.length, datetime.timedelta(0))

def apply_slip_days(students: Dict[int, Student], assignments: Dict[str, Assignment], categories: Dict[str, Category], extra_slip_days: Dict[int, Dict[str, int]]) -> None:
    """Applies slip days per category to students

    Slip days are applied using a brute-force method of enumerating all possible ways to assign slip days to assignments.

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

    for category in categories.values():
        assignments_in_category = list(filter(lambda a: a.category == category.name, assignments.values()))
        slip_possibilities = get_slip_possibilities(len(assignments_in_category), category.slip_days)
        for student in students.values():
            # Shallow copy student.grade_possibilities for concurrent modification
            for old_grade_possibility in list(student.grade_possibilities):
                for slip_possibility in slip_possibilities:
                    if sum(slip_possibility) == 0:
                        # Skip 0 case, which is already present
                        continue
                    possibility_with_slip = copy.deepcopy(old_grade_possibility)
                    for i in range(len(assignments_in_category)):
                        assignment = assignments_in_category[i]
                        slip_days = slip_possibility[i]
                        if assignment.name not in possibility_with_slip:
                            # Ignore non-present assignments in possibility
                            continue
                        possibility_with_slip[assignment.name].slip_days_applied = slip_days
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
    zero = datetime.timedelta(0)
    one = datetime.timedelta(days=1)
    for student in students.values():
        for grade_possibility in student.grade_possibilities:
            for grade in grade_possibility.values():
                lateness = grade.lateness
                lateness -= datetime.timedelta(days=grade.slip_days_applied)
                lateness = max(zero, lateness)
                days_late = lateness.days
                if lateness % one > zero:
                    days_late += 1

                assignment = assignments[grade.assignment_name]
                category = categories[assignment.category]
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

def main(args) -> None:
    roster_path = args.roster
    categories_path = args.categories
    assignments_path = args.assignments
    grades_path = args.grades
    extensions_path = args.extensions

    students = import_roster(roster_path)
    categories = import_categories(categories_path)
    assignments = import_assignments(assignments_path, categories)
    import_grades(grades_path, students, assignments)

    extensions = import_extensions(extensions_path)

    apply_extensions(students, extensions)
    apply_slip_days(students, assignments, categories, {})
    apply_late_multiplier(students, assignments, categories)

    print(list(students.values())[0].get_grade(assignments))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("roster", help="csv roster downloaded from CalCentral")
    parser.add_argument("categories", help="csv grades with assignment categories")
    parser.add_argument("assignments", help="csv with assignments")
    parser.add_argument("grades", help="csv grades from Gradescope")
    parser.add_argument("extensions", help="csv grades with extensions")
    #parser.add_argument("output_path", help="path where csv output should be saved")
    parser.add_argument("--config", "--c", help="yaml file of configs")
    parser.add_argument("--bins", "--b", help="yaml with letter grade bins")
    parser.add_argument("--accommodations", "--a", help="accommdations, if any. Accommodations should be a csv file with at least 3 columns: SID, Assignment, Days. An additional \"Clobbered by\" column should be present for clobbers")
    parser.add_argument("--round", "--r", type=int, default=5, help="Number of decimal places to round to")
    parser.add_argument("--histogram", "--h", help="path where histogram, if desired, should be saved")
    parser.add_argument("-v", "--verbose", action="count", help="verbosity")
    args = parser.parse_args()
    main(args)
