import sqlite3

# Connect (creates file if not exists)
conn = sqlite3.connect("todo.db")
cursor = conn.cursor()

# Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task TEXT NOT NULL,
    is_complete INTEGER DEFAULT 0
)
""")
conn.commit()


# Add task 
def add_task(task):
    cursor.execute("INSERT INTO tasks (task) VALUES (?)", (task,))
    conn.commit()
    print("✅ Task added!")

# View Tasks
def view_tasks():
    cursor.execute("SELECT * FROM tasks")
    rows = cursor.fetchall()
    for row in rows:
        status = "✔️" if row[2] else "❌"
        print(f"{row[0]}. {row[1]} [{status}]")


# Mark Complete
def mark_complete(task_id):
    cursor.execute("UPDATE tasks SET is_complete = 1 WHERE id = ?", (task_id,))
    conn.commit()
    print("✅ Task marked as complete!")

# Delete Task
def delete_task(task_id):
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    print("🗑️ Task deleted!")

# Menu driven program 
def menu():
    while True:
        print("\n📋 To-Do List Menu:")
        print("1. Add Task")
        print("2. View Tasks")
        print("3. Mark Task Complete")
        print("4. Delete Task")
        print("5. Exit")

        choice = input("Enter choice: ")

        if choice == "1":
            task = input("Enter task: ")
            add_task(task)
        elif choice == "2":
            view_tasks()
        elif choice == "3":
            task_id = int(input("Enter task ID to complete: "))
            mark_complete(task_id)
        elif choice == "4":
            task_id = int(input("Enter task ID to delete: "))
            delete_task(task_id)
        elif choice == "5":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Try again.")

menu()
