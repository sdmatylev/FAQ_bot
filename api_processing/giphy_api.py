import requests
from data.CONFIG import GIPHY_URL


class GiphyAPI:
    def __init__(self, logger):  # Конструктор инициализирует ключ и ссылку на api
        self.url = GIPHY_URL
        self.logger = logger

    def get_gif(self) -> str:  # Функция для получения ссылки на гифку, возвращает ссылку в виде текста
        try:
            response = requests.get(self.url).json()  # Отправляем запрос к api giphy

            return response['data']['images']['original']['url']  # Достаем ссылку из ответа и возвращаем
        except Exception as error:
            self.logger.save_log(error)
            return 'Не удалось загрузить gif'
