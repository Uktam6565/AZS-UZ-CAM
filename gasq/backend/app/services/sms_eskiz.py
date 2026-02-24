import httpx
from typing import Optional


class EskizSMS:
    """
    Eskiz.uz SMS client (OAuth token).
    ENV expected:
      - ESKIZ_EMAIL
      - ESKIZ_PASSWORD
      - ESKIZ_FROM (shortcode, e.g. 4546)
    """

    BASE_URL = "https://notify.eskiz.uz/api"

    def __init__(self, email: str, password: str, sender: str):
        self.email = email
        self.password = password
        self.sender = sender
        self._token: Optional[str] = None

    async def _login(self) -> str:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{self.BASE_URL}/auth/login",
                data={"email": self.email, "password": self.password},
            )
            r.raise_for_status()
            data = r.json()
            token = data.get("data", {}).get("token")
            if not token:
                raise RuntimeError("Eskiz login failed: token not found")
            self._token = token
            return token

    async def _get_token(self) -> str:
        if self._token:
            return self._token
        return await self._login()

    async def send_sms(self, phone: str, message: str) -> dict:
        """
        phone format: +998901234567 or 998901234567
        """
        token = await self._get_token()

        # Eskiz обычно принимает телефон без "+"
        cleaned = phone.strip().replace(" ", "")
        if cleaned.startswith("+"):
            cleaned = cleaned[1:]

        payload = {
            "mobile_phone": cleaned,
            "message": message,
            "from": self.sender,
        }

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{self.BASE_URL}/message/sms/send",
                data=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            # если токен протух — перелогинимся 1 раз
            if r.status_code == 401:
                self._token = None
                token = await self._login()
                r = await client.post(
                    f"{self.BASE_URL}/message/sms/send",
                    data=payload,
                    headers={"Authorization": f"Bearer {token}"},
                )

            r.raise_for_status()
            return r.json()
