import json
from pathlib import Path

# ---------- Student Class ----------
class Student:
    def __init__(self, roll_no, name):
        self.roll_no = roll_no
        self.name = name
        self.marks = {}  # subject: marks

    def add_mark(self, subject, mark):
        self.marks[subject] = mark

    def get_average(self):
        if not self.marks:
            return 0
        return sum(self.marks.values()) / len(self.marks)

    def get_grade(self):
        avg = self.get_average()
        if avg >= 90: return "A"
        elif avg >= 80: return "B"
        elif avg >= 70: return "C"
        elif avg >= 60: return "D"
        else: return "F"

    def to_dict(self):
        return {"name": self.name, "marks": self.marks}

    @staticmethod
    def from_dict(roll_no, data):
        s = Student(roll_no, data["name"])
        s.marks = data.get("marks", {})
        return s


# ---------- Gradebook Class ----------
class Gradebook:
    def __init__(self, filepath="gradebook.json"):
        self.students = {}
        self.filepath = Path(filepath)
        self.load()

    def add_student(self, roll_no, name):
        if roll_no in self.students:
            print(f"Student {roll_no} already exists.")
            return
        self.students[roll_no] = Student(roll_no, name)

    def add_mark(self, roll_no, subject, mark):
        if roll_no not in self.students:
            print("Student not found!")
            return
        self.students[roll_no].add_mark(subject, mark)

    def print_report(self, roll_no):
        if roll_no not in self.students:
            print("Student not found!")
            return
        s = self.students[roll_no]
        print(f"\nReport Card for {s.name} (Roll No: {s.roll_no})")
        print("-" * 40)
        for sub, mark in s.marks.items():
            print(f"{sub:15}: {mark}")
        print("-" * 40)
        print(f"Average: {s.get_average():.2f}")
        print(f"Grade: {s.get_grade()}")
        print("-" * 40)

    def save(self):
        data = {r: s.to_dict() for r, s in self.students.items()}
        self.filepath.write_text(json.dumps(data, indent=2))

    def load(self):
        if self.filepath.exists():
            data = json.loads(self.filepath.read_text())
            self.students = {r: Student.from_dict(r, s) for r, s in data.items()}
        else:
            self.students = {}


# ---------- Example Usage ----------
if __name__ == "__main__":
    gb = Gradebook()

    # Add students
    gb.add_student("103", "Alice")
    gb.add_student("104", "Bob")

    # Add marks
    gb.add_mark("103", "Math", 92)
    gb.add_mark("103", "English", 85)
    gb.add_mark("104", "Math", 78)
    gb.add_mark("104", "Science", 88)

    # Print reports
    gb.print_report("101")
    gb.print_report("102")
    gb.print_report("103")
    gb.print_report("104")


    # Save to file
    gb.save()
