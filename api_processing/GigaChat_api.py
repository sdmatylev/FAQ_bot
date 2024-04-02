from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from data.CONFIG import SBER_TOKEN
from data.ASSETS import prompt


class GigaChatAPI:
    def __init__(self, logger):  # Конструктор инициализирует модель и первичный промпт
        self.giga_chat = GigaChat(credentials=SBER_TOKEN, verify_ssl_certs=False)
        self.payload = Chat(
            messages=[
                Messages(
                    role=MessagesRole.SYSTEM,
                    content=prompt
                )
            ],
            temperature=1,
            max_tokens=500,
        )
        self.logger = logger

    def get_answer(self, request) -> str:  # Метод для отправки запроса к api, возвращает текстовый ответ
        try:  # Пробуем отправить запрос к GigaChat
            self.payload.messages.append(Messages(role=MessagesRole.USER, content=request))  # Добавляем в диалог сообщение пользователя
            response = self.giga_chat.chat(self.payload)  # Получаем ответ нейросети
            self.payload.messages.pop()  # Очищаем контекст

            return response.choices[0].message.content  # Возвращаем ответ
        except Exception as error:  # Ловим любую ошибку
            self.logger.save_log(error)
            return 'Не удалось отправить вопрос знатоку'
