"""Core utilities."""
import json
import os
import time
import requests

API = 'https://api.imgur.com/3/'
MAX_ATTEMPTS = 5
USAGE_LOG = 'usage.log'


def log_usage(request):
    """Log API usage information."""
    now = int(time.time())
    client_remaining = request.headers.get('X-RateLimit-ClientRemaining')
    user_remaining = request.headers.get('X-RateLimit-UserRemaining')
    reset = request.headers.get('X-RateLimit-UserReset')
    if not all((client_remaining, user_remaining, reset)):
        return
    delay = reset - now
    with open(USAGE_LOG, 'a') as log_file:
        log_file.write(','.join(map(str, (now, client_remaining,
                                          user_remaining, delay))))
        log_file.write('\n')


class Session:
    """Various token-based methods."""
    def __init__(self, token, bearer=True, log=True):
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
        self.log = log

    def _request(self, method, url, **kwargs):
        """Perform an API request."""
        attempt = 0
        while attempt < MAX_ATTEMPTS:
            req = method(API + url, headers={'Authorization': self.token}, **kwargs)
            if req.status_code >= 500:
                time.sleep(2**attempt)
                attempt += 1
                continue
            if self.log:
                log_usage(req)
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
