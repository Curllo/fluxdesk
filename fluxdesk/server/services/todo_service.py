from sqlalchemy.orm import Session
from models.database import Todo
import uuid


class TodoService:
    def __init__(self, db: Session):
        self.db = db

    def add(self, window_id: str, content: str, priority: int = 1):
        todo = Todo(
            id=f"todo_{uuid.uuid4().hex}",
            window_id=window_id,
            content=content,
            priority=priority,
        )
        self.db.add(todo)
        self.db.commit()
        return todo

    def list_by_window(self, window_id: str):
        return self.db.query(Todo).filter(Todo.window_id == window_id).all()

    def complete(self, todo_id: str):
        todo = self.db.query(Todo).filter(Todo.id == todo_id).first()
        if todo:
            todo.completed = 1
            self.db.commit()
        return todo

    def delete(self, todo_id: str):
        todo = self.db.query(Todo).filter(Todo.id == todo_id).first()
        if todo:
            self.db.delete(todo)
            self.db.commit()
        return todo
