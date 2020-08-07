import datetime

class Extension:
    def __init__(self, sid: int, assignment_name: str, length: datetime.timedelta) -> None:
        self.sid = sid
        self.assignment_name = assignment_name
        self.length = length

    def __repr__(self) -> str:
        return "Extension({}, '{}', {})".format(self.sid, self.assignment_name, repr(self.length))
