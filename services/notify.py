import os

import requests


class Notify:

    def __init__(self):
        self.__base_url = os.environ.get('NOTIFY_BASE_URL', 'http://localhost:8001')

    def send_order_event(self, data):
        response = requests.post(
            url=f'{self.__base_url}/api/v1/webhooks/order/',
            json=data,
            timeout=10,
        )
