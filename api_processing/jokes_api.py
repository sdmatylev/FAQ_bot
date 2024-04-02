import requests
from deep_translator import GoogleTranslator
from data.CONFIG import JOKES_URL


class JokesAPI:
    def __init__(self, logger):  # Конструктор инициализирует переводчик и ссылку на api
        self.translator = GoogleTranslator(source='en', target='ru')
        self.url = JOKES_URL
        self.logger = logger

    def get_joke(self) -> str:  # Метод для получения шутки от api, возвращает перевод шутки на русский язык
        try:
            response = requests.get(self.url).json()[0]  # Отправляем запрос к api joke-api

            return self.translator.translate(response['setup'] + '\n' + response['punchline'])
        except Exception as error:
            self.logger.save_log(error)
            return 'Не удалось загрузить шутку'
