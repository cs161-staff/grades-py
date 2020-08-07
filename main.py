import argparse
import csv
import datetime
from typing import Dict, List

from assignment import Assignment
from extension import Extension
from student import AssignmentGrade, Student

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

def import_assignments(path: str) -> Dict[str, Assignment]:
    """Imports assignments from the CSV file at the given path

    :param path: The path of the assignments CSV
    :type path: str
    :returns: A dict mapping assignment names to assignments
    :rtype: dict
    """
    assignments: Dict[str, Assignment] = {}
    with open(path) as assignment_file:
        reader = csv.DictReader(assignment_file)
        for row in reader:
            name = row["Name"]
            assignments[name] = Assignment(name)
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

            for assignment_name in assignments:
                assignment_lateness_header = "{} - Lateness (H:M:S)".format(assignment_name)

                scorestr = row[assignment_name]
                if scorestr == "":
                    # Empty string score string means no submission
                    continue
                score = float(scorestr)
                # Lateness formatted as HH:MM:SS
                lateness_components = row[assignment_lateness_header].split(":")
                lateness = datetime.timedelta(hours=int(lateness_components[0]), minutes=int(lateness_components[1]), seconds= int(lateness_components[2]))

                grade = AssignmentGrade(assignment_name, score, lateness)
                student.grades[assignment_name] = grade

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

    Extensions are applied by subtracting the length of the extension from the student's lateness for the assignment.

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
        if extension.assignment_name not in student.grades:
            # Skip assignments not in assignments list
            # Assignment will not be in student.grades if not in assignment list
            continue
        grade = student.grades[extension.assignment_name]
        grade.lateness = max(grade.lateness - extension.length, datetime.timedelta(0))

def main(args) -> None:
    roster_path = args.roster
    assignments_path = args.assignments
    grades_path = args.grades
    extensions_path = args.extensions

    students = import_roster(roster_path)
    assignments = import_assignments(assignments_path)
    import_grades(grades_path, students, assignments)

    extensions = import_extensions(extensions_path)

    apply_extensions(students, extensions)

    print(students)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("roster", help="csv roster downloaded from CalCentral")
    parser.add_argument("grades", help="csv grades from Gradescope")
    parser.add_argument("assignments", help="csv with assignments")
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
