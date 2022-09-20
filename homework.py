import logging
import sys
import os
import time

import requests
import telegram
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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler_recorder = logging.FileHandler('my_log.log')
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(funcName)s - %(message)s'
)
handler.setFormatter(formatter)
handler_recorder.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(handler_recorder)


def send_message(bot, message):
    """Конечная функция отправки сообщения."""
    logger.info('Попытка отправить сообщение')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Cообщение отправленно: {message}')
    except telegram.error.TelegramError as error:
        logger.error('сбой при отправке сообщения в Telegram '
                     f'ошибка: {error}')
        bot.send_message(TELEGRAM_CHAT_ID,
                         'сбой при отправке сообщения в Telegram '
                         f'ошибка: {error}')


def get_api_answer(current_timestamp):
    """делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    logger.info('Попытка отправить запрос')
    try:
        response = requests.get(ENDPOINT, headers=headers, params=params)
    except exceptions.ServerError as error:
        logger.error(f'ошибка при запросе к эндпоинту {error}')
    if response.status_code != 200:
        raise exceptions.StatusCodeError('API не вернула 200')
    logger.info('Ответ от API успешно получен')
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
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    env_list = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(env_list)


def main():
    """Основная логика работы бота."""
    logger.info("Starting")
    if not check_tokens():
        logger.error('Отсутствие обязательных переменных')
        sys.exit('Отсутствие обязательных переменных '
                 'окружения во время запуска бота')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    current_timestamp = int(time.time())
    perv_status = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            response_list = check_response(response)
            current_timestamp = response.get('current_date', current_timestamp)
            if len(response_list) > 0:
                homework = response_list[0]
                current_status = parse_status(homework)
                if current_status != perv_status:
                    perv_status = current_status
                    message = current_status
                    send_message(bot, message)
            else:
                logger.debug('отсутствие в ответе новых статусов')
        except exceptions.ServerError as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.exception('сбой при отправке сообщения в Telegram')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
