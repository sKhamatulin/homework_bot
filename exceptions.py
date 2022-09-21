class StatusCodeError(Exception):
    """Вызывается когда API не вернула 200."""

    pass


class ResponseAPIError(Exception):
    """Некоректные данные в ответе API."""

    pass


class ServerError(Exception):
    """Невозможно подключится к серверу."""

    pass


class SendError(Exception):
    """Ошибка при отправке сообщения."""

    pass
