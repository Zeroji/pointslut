"""Core utilities."""
import os


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
