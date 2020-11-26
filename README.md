# CS 161 Grading Script v2

This grading script is intended to automate the grading process of CS 161 by
automatically applying various grading policies such as slip days and drops as
well as allowing for per-student accommodations and extensions on assignments.

The script will take in four required files: a CSV roster export from
CalCentral, a CSV grade report from Gradescope, a CSV containing assignment
category data, and a CSV containing assignment data. You may optionally also
specify a CSV file containing per-student extensions and a CSV file containing
per-student accommodations for homework drops and slip days.

The script automatically runs all the grade calculations and outputs a grade
report for each student to STDOUT, formatted as a CSV. This may then be imported
into any spreadsheet program for further analysis.

You will need Python 3 to run this script.

## Usage

```
python3 main.py <roster> <grades> <categories> <assignments> [--extensions EXTENSIONS] [--accommodations ACCOMMODATIONS] > output.csv
```

## Input Specifications

Example inputs are provided in the `examples` folder, with a single student and
the assignment/category layout taken from Summer 2020.

### CalCentral Roster

The CalCentral roster is used to output grades for only students who are
enrolled in the class. The following columns are required (and are automatically
generated by CalCentral):

| Column | Description |
| ------ | ----------- |
| `Name` | A student's name, in `Last, First` format |
| `Student ID` | A student's SID |

Note that many other fields are included in a standard CalCentral roster export.

### Gradescope Grades

The Gradescope grades is the main source of grading data, exported from the
Assignments page of Gradescope. This contains the raw score, the max score, the
submission time, and the lateness of each submission for each student. The
following columns are required (and are automatically generated by Gradescope):

| Column | Description |
| ------ | ----------- |
| `SID`  | A student's SID |
| `ASSIGNMENT` | The student's score on **ASSIGNMENT** |
| `ASSIGNMENT - Lateness (H:M:S)` | How late the student submitted **ASSIGNMENT**, formatted as `(HH:MM:SS)` |
| `ASSIGNMENT - Max Points` | The maximum number of points a student may receive on **ASSIGNMENT** |

Each of the last three columns is included for each assignment, so there will be
a variable number of columns in the Gradescope export depending on the number of
assignments in Gradescope. **Grades will not be processed if not present in the
assignments CSV.**

Note that several other fields are included in a standard Gradescope export.

### Categories CSV

The categories CSV contains categories that each assignment must be a part of.
It defines the behavior of each category and which grading policies will be
applied to assignments in each category. The following columns are required:

| Column | Description |
| ------ | ----------- |
| `Name` | The name of the category |
| `Weight` | The weight of the category |
| `Drops` | The number of drops provided in this category |
| `Slip Days` | The number of slip days provided in this category |
| `Has Late Multiplier` | `0` if the category does not allow late work and `1` if the category allows a late multiplier |

The values in `Weight` must sum to 1.0---**the script will not verify this**.

### Assignments CSV

The assignments CSV defines assignments that will be handled as part of grading.
**These assignment names must match exactly their names on Gradescope.** The
following columns are required:

| Column | Description | 
| ------ | ----------- |
| `Name` | The name of the assignment |
| `Category` | The name of the assignment's category |
| `Possible` | The number of points possible on the assignment |
| `Weight` | The weight of the assignment **within the category** |
| `Slip Group` | Used to group assignments together so that they share a lateness and slip day application (e.g. a writeup and autograder for the same project due at the same time) |

Note that the `Possible` field is different from the `ASSIGNMENT - Max Points`
field in the Gradescope export. The former defines the denominator used for
calculating the assignment's grade, while the latter is used to define a ceiling
on the raw score a student may have on an assignment, before dividing by the
denominator.

The `Weight` field is different in that the columns need not sum to 1.0, since
we allow drops to any arbitrary assignment, which can affect category scores in
different ways. Thus, for all assignments to be weighted equally, you may have a
`1.0` in every assignment.

### Extensions CSV

The extension CSV defines assignment deadline extensions to students such that
the late multiplier will not be applied. The following columns are required:

| Column | Description |
| ------ | ----------- |
| `SID` | The student's SID |
| `Assignment` | The name of the assignment whose deadline is being extended |
| `Days` | The number of days the deadline is extended by |

### Accommodations CSV

The accommodations CSV defines individual accommodations given to students in
the form of additional slip days or drops within specific categories. The
following columns are required:

| Column | Description |
| ------ | ----------- |
| `SID` | The student's SID |
| `Category` | The category relevant to the accommodation |
| `Drop Adjust` | The number of additional drops to grant in the category |
| `Slip Day Adjust` | The number of additional slip days to grant in the category |

`Drop Adjust` and `Slip Day Adjust` may technically be negative, which would
have the effect of removing slip days and drops the student would otherwise
receive, but this likely is not a useful feature.

## Grade Calculation

This script is constructed to enumerate all possibilities of applying grading
policies (such as all ways to assign slip days and/or drops) and choosing the
option that most benefits the student. Each `Student` has a
`grade_possibilities` list that represents one possibility. Each application of
course policies and individual accommodations (the `apply_*` functions) will
mutate each student's `grade_possibilities` list, increasing its length if there
are multiple possibilities for this course policy (e.g. slip days). For simpler
policies, such as extensions, the possibility list will be mutated in place
without adding new possibilities for the sake of efficiency and reasonable
optimization (e.g. there is no circumstance in which not applying a homework
drop would be more beneficial).

After all policies and accommodations are applied, the grade calculation is run
for all policies for each student, and the final grade assigned to them is the
highest possible grade they can receive. A grade report is also generated that
shows the breakdown for each assignment and category, their contributions to the
final grade, and comments showing policies applied for the sake of transparency.

## Features

- Slip days within categories, allowing a certain number of late days across all
  assignments without a late multiplier
- Drops within categories, dropping the assignment that most negatively impacts
  the grade
  - Does not guarantee optimal grade for student with unequally weighted
    assignments for the time being
- Extensions on assignments for individual students
- Additional slip days in categories for individual students
- Additional drops in categories for individual students
- Late multipliers
  - Currently fixed at `[0.9, 0.8, 0.6]`, or 10%, 20%, 40% grade reduction

## Future Development

This script is written with extensibility in mind, needing only to branch out
more possibilities or mutating existing possibilities for students. However,
ideally, this script will not do more than it needs to, since features such as
grade bins can be done externally. As a rule of thumb, if you can do it easily
in Excel, use Excel on the output of this script.

That being said, logical additions for future features include the following:

- Manual grade overrides on individual assignments, with an optional comment
  - This handles individual clobber accommodations and other one-off grade
    overrides
