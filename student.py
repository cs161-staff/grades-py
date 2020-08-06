class Student:
    def __init__(self, sid: int, name: str) -> None:
        self.sid = sid
        self.name = name

    def __repr__(self) -> str:
        return "Student({}, \"{}\")".format(self.sid, self.name)
