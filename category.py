class Category:
    def __init__(self, name: str, weight: float, drops: int, slip_days: int, has_late_multiplier: bool = False) -> None:
        self.name = name
        self.weight = weight
        self.drops = drops
        self.slip_days = slip_days
        self.has_late_multiplier = has_late_multiplier

    def __repr__(self) -> str:
        return f'Category({self.name}, {self.weight}, {self.drops}, {self.slip_days}, {self.has_late_multiplier})'
