import requests
import os

class Notification:

    def __init__(self) -> None:
        pass

    def push(self, text):
        requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": os.getenv("PUSHOVER_TOKEN"),
                "user": os.getenv("PUSHOVER_USER"),
                "message": text,
            }
        )