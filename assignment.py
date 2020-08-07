class Assignment:
    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return "Assignment(\"{}\")".format(self.name)
