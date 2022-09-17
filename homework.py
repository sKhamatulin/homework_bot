import logging
import sys
import os
import time
import requests

from telegram import Bot

from dotenv import load_dotenv

from logging import StreamHandler

load_dotenv()


PRACTICUM_TOKEN = os.getenv('YA_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

TEST_TIME = 2629743  # месяц

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Конечная функция отправки сообщения."""
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    response = requests.get(ENDPOINT, headers=headers, params=params)
    if response.status_code != 200:
        logging.error('недоступность эндпоинта')
        raise Exception('API вернула 200')
    return response.json()


def check_response(response):
    """проверяет ответ API на корректность."""
    if response == {}:
        logging.error('яндекс вернул пустой словарь')
        raise Exception('яндекс вернул пустой словарь')
    elif type(response['homeworks']) != list:
        logging.error('под ключом `homeworks` домашки'
                      'приходят не в виде списка')
        raise Exception('под ключом `homeworks` домашки'
                        'приходят не в виде списка')
    elif 'homeworks' not in response.keys():
        logging.error('ответ от API не содержит ключа `homeworks`')
        raise Exception('ответ от API не содержит ключа `homeworks`')
    return response['homeworks']


def parse_status(homework):
    """Извлекает из словаря статус работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'
    return message


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID is not None:
        return True
    return False


def main():
    """Основная логика работы бота."""
    if check_tokens() is True:
        bot = Bot(token=TELEGRAM_TOKEN)
    else:
        logging.critical('отсутствие обязательных переменных'
                         'окружения во время запуска бота')
        raise Exception('Сбой при проверке токенов')

    current_timestamp = int(time.time()) - TEST_TIME
    # отладочный вариант, что бы приходило первое сообщение
    while True:
        try:
            response = get_api_answer(current_timestamp)
            response_list = check_response(response)
            if len(response_list) > 0:
                homework = response_list[0]
                message = parse_status(homework)
                send_message(bot, message)
                logging.info('удачная отправка сообщения'
                             f'{message} в Telegram')
            else:
                logging.debug('отсутствие в ответе новых статусов')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
            logging.error('сбой при отправке сообщения в Telegram')
        else:
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
