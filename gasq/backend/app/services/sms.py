class SmsService:
    """
    Временная SMS-заглушка.
    Позже заменим на Eskiz без изменения бизнес-логики.
    """

    async def send(self, phone: str, message: str):
        print("=== SMS MOCK ===")
        print("TO:", phone)
        print("MESSAGE:", message)
        print("================")
        return {"ok": True, "mock": True}
