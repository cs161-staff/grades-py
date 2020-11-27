class Category:
    def __init__(self, name: str, weight: float, has_late_multiplier: bool = False) -> None:
        # Slip days and drops are tracked per student, not in Category
        self.name = name
        self.weight = weight
        self.has_late_multiplier = has_late_multiplier

    def __repr__(self) -> str:
        return f'Category({self.name}, {self.weight}, {self.has_late_multiplier})'
