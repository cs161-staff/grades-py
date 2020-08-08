class Assignment:
    def __init__(self, name: str, category: str, score_possible: float, weight: float, slip_group: int) -> None:
        self.name = name
        self.category = category
        self.score_possible = score_possible
        self.weight = weight
        self.slip_group = slip_group

    def __repr__(self) -> str:
        return "Assignment('{}', '{}', {}, {}, {})".format(self.name, self.category, self.score_possible, self.weight, self.slip_group)
