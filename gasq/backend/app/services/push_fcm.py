from typing import Optional

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except Exception:  # noqa
    firebase_admin = None
    credentials = None
    messaging = None


class FCMService:
    """
    Firebase Cloud Messaging sender.
    ENV expected:
      - FCM_SERVICE_ACCOUNT_PATH  (path to service-account json file)
    """

    def __init__(self, service_account_path: str):
        self.service_account_path = service_account_path
        self._initialized = False

    def _init(self) -> None:
        if self._initialized:
            return
        if firebase_admin is None:
            raise RuntimeError("firebase-admin not installed. Add it to requirements.txt")

        # avoid "already exists" error when reload
        if not firebase_admin._apps:
            cred = credentials.Certificate(self.service_account_path)
            firebase_admin.initialize_app(cred)
        self._initialized = True

    def send_to_token(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[dict] = None,
    ) -> str:
        self._init()
        msg = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
        )
        return messaging.send(msg)
