class Assignment:
    def __init__(self, name: str, score_possible: float, weight: float) -> None:
        self.name = name
        self.score_possible = score_possible
        self.weight = weight

    def __repr__(self) -> str:
        return "Assignment('{}')".format(self.name)
