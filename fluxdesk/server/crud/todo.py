from typing import List, Optional
from sqlalchemy.orm import Session
from models.database import Todo


class TodoCRUD:
    def __init__(self, db: Session):
        self.db = db

    def create(self, content: str, priority: int = 1, due_at: str = None, window_id: str = None) -> Todo:
        todo = Todo(content=content, priority=priority, due_at=due_at, window_id=window_id)
        self.db.add(todo)
        self.db.commit()
        self.db.refresh(todo)
        return todo

    def get(self, todo_id: str) -> Optional[Todo]:
        return self.db.query(Todo).filter(Todo.id == todo_id).first()

    def list_all(self, completed: bool = None) -> List[Todo]:
        q = self.db.query(Todo)
        if completed is not None:
            q = q.filter(Todo.completed == (1 if completed else 0))
        return q.order_by(Todo.created_at.desc()).all()

    def complete(self, todo_id: str) -> Optional[Todo]:
        from datetime import datetime
        todo = self.get(todo_id)
        if todo:
            todo.completed = 1
            todo.completed_at = datetime.now().isoformat()
            self.db.commit()
            self.db.refresh(todo)
        return todo

    def update(self, todo_id: str, **kwargs) -> Optional[Todo]:
        todo = self.get(todo_id)
        if not todo:
            return None
        for k, v in kwargs.items():
            if hasattr(todo, k):
                setattr(todo, k, v)
        self.db.commit()
        self.db.refresh(todo)
        return todo

    def delete(self, todo_id: str) -> bool:
        todo = self.get(todo_id)
        if todo:
            self.db.delete(todo)
            self.db.commit()
            return True
        return False
