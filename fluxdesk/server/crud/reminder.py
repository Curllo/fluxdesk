from typing import List, Optional
from sqlalchemy.orm import Session
from models.database import Reminder


class ReminderCRUD:
    def __init__(self, db: Session):
        self.db = db

    def create(self, title: str, time: str, repeat: str = "once") -> Reminder:
        r = Reminder(title=title, time=time, repeat=repeat)
        self.db.add(r)
        self.db.commit()
        self.db.refresh(r)
        return r

    def get(self, reminder_id: str) -> Optional[Reminder]:
        return self.db.query(Reminder).filter(Reminder.id == reminder_id).first()

    def list_all(self, dismissed: bool = None) -> List[Reminder]:
        q = self.db.query(Reminder)
        if dismissed is not None:
            q = q.filter(Reminder.dismissed == (1 if dismissed else 0))
        return q.order_by(Reminder.time).all()

    def dismiss(self, reminder_id: str) -> Optional[Reminder]:
        r = self.get(reminder_id)
        if r:
            r.dismissed = 1
            self.db.commit()
            self.db.refresh(r)
        return r

    def delete(self, reminder_id: str) -> bool:
        r = self.get(reminder_id)
        if r:
            self.db.delete(r)
            self.db.commit()
            return True
        return False
