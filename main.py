import argparse
import csv
import datetime
from typing import Dict

from assignment import Assignment
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
                # Skip students who aren't in the roster
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

def main(args) -> None:
    roster_path = args.roster
    assignments_path = args.assignments
    grades_path = args.grades

    students = import_roster(roster_path)
    assignments = import_assignments(assignments_path)
    import_grades(grades_path, students, assignments)
    print(students)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("roster", help="csv roster downloaded from CalCentral")
    parser.add_argument("grades", help="csv grades from Gradescope")
    parser.add_argument("assignments", help="csv with assignments")
    #parser.add_argument("output_path", help="path where csv output should be saved")
    parser.add_argument("--config", "--c", help="yaml file of configs")
    parser.add_argument("--bins", "--b", help="yaml with letter grade bins")
    parser.add_argument("--accommodations", "--a", help="accommdations, if any. Accommodations should be a csv file with at least 3 columns: SID, Assignment, Days. An additional \"Clobbered by\" column should be present for clobbers")
    parser.add_argument("--round", "--r", type=int, default=5, help="Number of decimal places to round to")
    parser.add_argument("--histogram", "--h", help="path where histogram, if desired, should be saved")
    parser.add_argument("-v", "--verbose", action="count", help="verbosity")
    args = parser.parse_args()
    main(args)
