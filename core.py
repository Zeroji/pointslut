"""Core utilities."""
import configparser
import json
import logging
import os
import time
import requests

# pylint: disable=C0103
log = logging.getLogger()

API = 'https://api.imgur.com/3/'

CFG = configparser.ConfigParser()
CFG.add_section('core')
CFG.add_section('paths')
CFG.read('config.ini')


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
    client_remaining = int(client_remaining)
    user_remaining = int(user_remaining)
    reset = int(reset)
    if client_remaining < 1000 and client_remaining % 200 == 0:
        log.WARN('API Usage: %s client credits remaining', client_remaining)
    if user_remaining < 1000 and user_remaining % 200 == 0:
        log.WARN('API Usage: %s user credits remaining', user_remaining)
    delay = reset - now
    with open(CFG['paths'].get('usage log', 'usage.log'), 'a') as log_file:
        log_file.write(','.join(map(str, (now, client_remaining,
                                          user_remaining, delay))))
        log_file.write('\n')


class Session:
    """Various token-based methods."""

    _proxy_index = 0
    _proxy_list = []

    @staticmethod
    def _next_proxy():
        if not Session._proxy_list and os.path.isfile(CFG['paths'].get('proxy list')):
            with open(CFG['paths'].get('proxy list'), 'r') as proxy_file:
                Session._proxy_list = json.load(proxy_file)
        proxy = Session._proxy_list[Session._proxy_index % len(Session._proxy_list)]
        Session._proxy_index += 1
        return {'https': proxy}

    @staticmethod
    def _dict_token(data):
        token = data['token']
        if 'token_type' in data:
            token = ('%s %s') % (data['token_type'], token)
        return token

    def __init__(self, token, bearer=True, log_usage=True, proxied=False):
        """Create a session."""
        if isinstance(token, dict):
            token = self._dict_token(token)
        if os.path.isfile(token):
            with open(token, 'r') as token_file:
                token = token_file.read().strip()
        try:
            data = json.loads(token)
            token = self._dict_token(data)
        except json.JSONDecodeError:
            pass
        if ' ' in token:
            self.token = token
        else:
            if bearer:
                self.token = f'Bearer {token}'
            else:
                self.token = f'Client-ID{token}'
        self.log_usage = log_usage
        self.proxy = None
        if proxied:
            self.proxy = Session._next_proxy()

    def _request(self, method, url, **kwargs):
        """Perform an API request."""
        attempt = 0
        while attempt < CFG['core'].getint('max attempts', 5):
            try:
                req = method(API + url,
                             headers={'Authorization': self.token},
                             proxies=self.proxy, **kwargs)
            except requests.exceptions.ProxyError:
                log.debug('ProxyError on %s, replacing', self.proxy['https'])
                self.proxy = self._next_proxy()
                continue
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
        req = self._request(requests.post, url, data=data)
        if isinstance(req['data'], dict) and 'error' in req['data']:
            error = req['data']['error']
            if isinstance(error, dict) and error['code'] == 429:
                # Rate limit, wait X minutes before uploading
                delay = int(error['message'].split('wait ')[1].split()[0])
                log.info('Rate limited, waiting %d minutes', delay)
                time.sleep(delay * 60)
                req = self._request(requests.post, url, data=data)
        return req

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
        data['image'] = link
        req = self.post('image', data=data)
        if not req['success']:
            log.warning('Uploading %s failed, skipping', link)
            return False
        uid = req['data']['id']
        log.debug('Successfully uploaded %s as %s', link, uid)
        return uid

    def upload_album(self, album, lambdas=None):
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
        nID = req['data']['id']
        log.info('Successfully uploaded album %s as %s. Uploading %d images...',
                 aID, nID, count)
        success = 0
        for i, image in enumerate(images):
            if lambdas is not None:
                for func in lambdas:
                    image = func(image, i, success, album)
                    if image is None:
                        break
                if image is None:
                    continue
            if self.upload(image, album=nID):
                success += 1
            if (i - success) / count > (1 - CFG['core'].getfloat('success rate', 0.8)):
                # There are too many failed images to reach the ratio
                break
        if success == 0 or (success < count * CFG['core'].getfloat('success rate', 0.8)):
            log.warning('Aborting album %s (%s), not enough images (%d out of %d)',
                        nID, aID, success, count)
            return False
        return nID
