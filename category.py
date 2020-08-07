class Category:
    def __init__(self, name: str, drops: int = 0, slip_days: int = 0) -> None:
        self.name = name
        self.drops = drops
        self.slip_days = slip_days

    def __repr__(self) -> str:
        return "Category('{}', {}, {})".format(self.name, self.drops, self.slip_days)
