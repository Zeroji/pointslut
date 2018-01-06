"""Core utilities."""
import json
import logging
import os
import time
import requests

# pylint: disable=C0103
log = logging.getLogger()

API = 'https://api.imgur.com/3/'
CFG_PATH = 'config.json'
MAX_ATTEMPTS = 5
USAGE_LOG = 'usage.log'
ALBUM_RATIO = 0.8

if os.path.isfile(CFG_PATH):
    CONFIG = {}
    with open(CFG_PATH, 'r') as config_file:
        CONFIG = json.load(config_file)
    MAX_ATTEMPTS = CONFIG.get('max_attempts', MAX_ATTEMPTS)
    USAGE_LOG = CONFIG.get('usage_log', USAGE_LOG)
    ALBUM_RATIO = CONFIG.get('album_ratio', ALBUM_RATIO)


def copy_keys(data, *keys):
    """Create a subset of a dict, discarding empty values."""
    return {key: value for key, value in data.items() if key in keys and value}


def _log_usage(request):
    """Log API usage information."""
    now = int(time.time())
    client_remaining = request.headers.get('X-RateLimit-ClientRemaining')
    user_remaining = request.headers.get('X-RateLimit-UserRemaining')
    reset = request.headers.get('X-RateLimit-UserReset')
    if not all((client_remaining, user_remaining, reset)):
        return
    if client_remaining < 1000 and client_remaining % 200 == 0:
        log.WARN('API Usage: %s client credits remaining', client_remaining)
    if user_remaining < 1000 and user_remaining % 200 == 0:
        log.WARN('API Usage: %s user credits remaining', user_remaining)
    delay = reset - now
    with open(USAGE_LOG, 'a') as log_file:
        log_file.write(','.join(map(str, (now, client_remaining,
                                          user_remaining, delay))))
        log_file.write('\n')


class Session:
    """Various token-based methods."""

    def __init__(self, token, bearer=True, log_usage=True):
        """Create a session."""
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
        self.log_usage = log_usage

    def _request(self, method, url, **kwargs):
        """Perform an API request."""
        attempt = 0
        while attempt < MAX_ATTEMPTS:
            req = method(API + url, headers={'Authorization': self.token}, **kwargs)
            if req.status_code >= 500:
                delay = 2**attempt
                attempt += 1
                log.debug('Request #%d failed with code %d, retrying in %d seconds',
                          attempt, req.status_code, delay)
                time.sleep(delay)
                continue
            if self.log_usage:
                _log_usage(req)
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

    def upload(self, image, album=None):
        """Reupload an image. Return ID or False."""
        data = copy_keys(image, 'title', 'description')
        data['type'] = 'URL'
        if album is not None:
            data['album'] = album
        link = image['link']
        if image['animated']:
            # GIFs seem to be linked as thumbnails named [ID]h.gif
            link = link.replace('h.gif', '.gif')
        req = self.post('image', data=data)
        if not req['success']:
            log.warning('Uploading %s failed, skipping', link)
            return False
        uid = req['data']['id']
        log.debug('Successfully uploaded %s as %s', link, uid)
        return uid

    def upload_album(self, album):
        """Reupload an album. Return ID or False."""
        aID = album['id']
        count = album['images_count']
        images = album['images']
        if count != len(images):
            log.debug('Requesting entire album %s', aID)
            req = self.get('gallery/album/%s' % aID)
            if not req['success']:
                log.warning('Couldn\'t retrieve entire album %s, aborting', aID)
                log.debug(req)
                return False
            images.clear()
            images.extend(req['data']['images'])
        data = copy_keys(album, 'title', 'topic', 'description', 'cover')
        req = self.post('album', data=data)
        if not req['success']:
            log.warning('Failed to reupload %s, aborting', aID)
            return False
        nID = req['data']['album']
        log.info('Successfully uploaded album %s as %s. Uploading %d images...',
                 aID, nID, count)
        success = 0
        for i, image in enumerate(images):
            if self.upload(image, album=nID):
                success += 1
            if (i - success) / count > (1 - ALBUM_RATIO):
                # There are too many failed images to reach the ratio
                break
        if success == 0 or (success < count * ALBUM_RATIO):
            log.warning('Aborting album %s (%s), not enough images (%d out of %d)',
                        nID, aID, success, count)
        return nID
