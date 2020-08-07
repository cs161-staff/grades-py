class Assignment:
    def __init__(self, name: str, category: str, score_possible: float, weight: float) -> None:
        self.name = name
        self.category = category
        self.score_possible = score_possible
        self.weight = weight

    def __repr__(self) -> str:
        return "Assignment('{}')".format(self.name)
