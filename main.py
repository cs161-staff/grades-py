import argparse
import csv
from typing import List

from student import Student

def import_roster(path: str) -> List[Student]:
    students: List[Student] = []
    with open(path) as roster_file:
        reader = csv.DictReader(roster_file)
        for row in reader:
            sid = int(row["Student ID"])
            name = row["Name"]
            students.append(Student(sid, name))
    return students

def main(args) -> None:
    roster_path = args.roster
    grades_path = args.grades

    roster = import_roster(roster_path)
    print(roster)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("roster", help="csv roster downloaded from CalCentral")
    parser.add_argument("grades", help="csv grades from Gradescope")
    #parser.add_argument("weights", help="csv with weights for each assignment")
    #parser.add_argument("output_path", help="path where csv output should be saved")
    parser.add_argument("--config", "--c", help="yaml file of configs")
    parser.add_argument("--bins", "--b", help="yaml with letter grade bins")
    parser.add_argument("--accommodations", "--a", help="accommdations, if any. Accommodations should be a csv file with at least 3 columns: SID, Assignment, Days. An additional \"Clobbered by\" column should be present for clobbers")
    parser.add_argument("--round", "--r", type=int, default=5, help="Number of decimal places to round to")
    parser.add_argument("--histogram", "--h", help="path where histogram, if desired, should be saved")
    parser.add_argument("-v", "--verbose", action="count", help="verbosity")
    args = parser.parse_args()
    main(args)
