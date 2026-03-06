class SmsService:
    """
    Временная SMS-заглушка.
    Позже заменим на Eskiz без изменения бизнес-логики.
    """

    async def send(self, phone: str, message: str):
        # временный mock SMS сервис (для разработки)
        # в production будет интеграция с Eskiz
        return {
            "ok": True,
            "mock": True,
            "phone": phone,
        }
