import logging
import sys
import os
import time

import requests
from telegram import Bot
from dotenv import load_dotenv

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('YA_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
logging.basicConfig(
    level=logging.INFO,
    filename='my_log.log',
    format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s'
)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(funcName)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Конечная функция отправки сообщения."""
    logging.info('Попытка отправить сообщение')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Cообщение отправленно')
    except exceptions.SendError as error:
        logging.error('сбой при отправке сообщения в Telegram '
                      f'ошибка: {error}')


def get_api_answer(current_timestamp):
    """делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    logging.info('Попытка отправить запрос')
    response = requests.get(ENDPOINT, headers=headers, params=params)
    if response.status_code != 200:
        raise exceptions.StatusCodeError('API не вернула 200')
    logging.info('Ответ от API успешно получен')
    return response.json()


def check_response(response):
    """проверяет ответ API на корректность."""
    if not isinstance(response['homeworks'], list):
        raise exceptions.ResponseAPIError('под ключом `homeworks` домашки '
                                          'приходят не в виде списка')
    if 'homeworks' not in response.keys():
        raise exceptions.ResponseAPIError('ответ от API не содержит '
                                          'ключа `homeworks`')
    return response['homeworks']


def parse_status(homework):
    """Извлекает из словаря статус работы."""
    if not isinstance(homework, dict):
        raise TypeError('homework '
                        'не является словарём')
    if 'status' not in homework.keys():
        raise KeyError('homework '
                       'не содержит ключа status')
    if 'homework_name' not in homework.keys():
        raise KeyError('homework '
                       'не содержит ключа homework_name')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS.keys():
        raise KeyError(f'{homework_status} не является '
                       'ключом для HOMEWORK_STATUSES')
    verdict = HOMEWORK_VERDICTS[homework_status]
    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'
    return message


def check_tokens():
    """Проверяет доступность переменных окружения."""
    env_list = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if all(env_list) is True:
        return True
    return False


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Отсутствие обязательных переменных '
                 'окружения во время запуска бота')
    bot = Bot(token=TELEGRAM_TOKEN)

    current_timestamp = int(time.time())
    perv_status = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            response_list = check_response(response)
            if len(response_list) > 0:
                homework = response_list[0]
                current_status = parse_status(homework)
                if current_status != perv_status:
                    perv_status = current_status
                    message = current_status
                    send_message(bot, message)
                    current_timestamp = response.get('current_date',
                                                     current_timestamp)
                    logging.info('удачная отправка сообщения '
                                 f'{message} в Telegram')
                logging.info('статус проверки прежний')
            else:
                logging.debug('отсутствие в ответе новых статусов')
        except exceptions.ServerError as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logging.exception('сбой при отправке сообщения в Telegram')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
