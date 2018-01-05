"""Core utilities."""
import os
import time
import requests

API = 'https://api.imgur.com/3/'
MAX_ATTEMPTS = 5


class Session:
    """Various token-based methods."""
    def __init__(self, token, bearer=True):
        if os.path.isfile(token):
            with open(token, 'r') as token_file:
                token = token_file.read().strip()
        if ' ' in token:
            self.token = token
        else:
            if bearer:
                self.token = f'Bearer {token}'
            else:
                self.token = f'Client-ID{token}'

    def _request(self, method, url, **kwargs):
        """Perform an API request."""
        attempt = 0
        while attempt < MAX_ATTEMPTS:
            req = method(API + url, headers={'Authorization': self.token}, **kwargs)
            if req.status_code >= 500:
                time.sleep(2**attempt)
                attempt += 1
                continue
            return req.json()
        return {'success': False}

    def get(self, url):
        """Perform a GET request on the API."""
        return self._request(requests.get, url)

    def post(self, url, data=None):
        """Perform a POST request on the API."""
        if data is None:
            data = {}
        return self._request(requests.post, url, data=data)
