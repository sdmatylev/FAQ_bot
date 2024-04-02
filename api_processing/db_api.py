import firebase_admin
from firebase_admin import credentials, db
from typing import Optional
from data.CONFIG import DB_URL


class DbAPI:
    def __init__(self):
        self.cred = credentials.Certificate('data/firebase_key.json')
        firebase_admin.initialize_app(self.cred, {'databaseURL': DB_URL})
        self.root = db.reference()

    def add_data_to_table(self, table: str, key: str, data: dict) -> None:
        self.root.child(table).child(key).set(data)

    def load_data_from_table(self, table: str, key: Optional[str] = None):
        if key is None:
            return self.root.child(table).get()
        else:
            return self.root.child(table).child(key).get()

    def update_table_data(self, table: str, key: str, new_data: dict) -> None:
        self.root.child(table).child(key).set(new_data)

    def delete_data_from_table(self, table: str, key: str) -> None:
        self.root.child(table).child(key).delete()

    @property
    def load_questions(self):  # Загрузка вопросов и ответов из бд
        questions = {}
        for data in self.load_data_from_table('questions')[1:]:
            questions[data['question']] = data['answer']

        return questions
