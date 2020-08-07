class Category:
    def __init__(self, name: str, weight: float, drops: int = 0, slip_days: int = 0, has_late_multiplier: bool = False) -> None:
        self.name = name
        self.weight = weight
        self.drops = drops
        self.slip_days = slip_days
        self.has_late_multiplier = has_late_multiplier

    def __repr__(self) -> str:
        return "Category('{}', {}, {}, {}, {})".format(self.name, self.weight, self.drops, self.slip_days, self.has_late_multiplier)
