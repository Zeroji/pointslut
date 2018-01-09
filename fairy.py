"""Cute little helpers."""
import configparser
import json
import logging
import os
import re
import concurrent.futures
import core

# pylint: disable=W0104
_CFG = configparser.ConfigParser()
_CFG.add_section('fairy')
_CFG.read('config.ini')
CFG = _CFG['fairy']

# pylint: disable=C0103
log = logging.getLogger()


class Swarm:
    """Lots of cute little helpers."""

    def __init__(self, tokens=None, proxied=True, threaded=False):
        """Initialize with tokens."""
        self.fairies = []
        self.proxied = proxied
        self.threaded = threaded
        self.executor = None
        self.futures = []
        if threaded:
            self.executor = concurrent.futures.ThreadPoolExecutor()
        if isinstance(tokens, str) and os.path.exists(tokens):
            with open(tokens, 'r') as tokens_file:
                tokens = json.load(tokens_file)
        if isinstance(tokens, dict):
            tokens = list(tokens.values())
        if isinstance(tokens, list):
            for token in tokens:
                self.fairies.append(core.Session(token, log_usage=not threaded,
                                                 proxied=proxied))
        log.info('Initialized swarm with %d fairies', len(self.fairies))

    @staticmethod
    def _aggregate(results):
        """Bundle several request results into one."""
        successes = 0
        errors = []
        failure_code = 400
        success_code = 200
        success_data = None
        for res in results:
            if res['success']:
                successes += 1
                success_code = res['status']
                success_data = res['data']
            else:
                failure_code = res['status']
                errors.append(res['status'])
        if successes / len(results) < CFG.getfloat('success rate'):
            return {'data': errors, 'status': failure_code, 'success': False}
        return {'data': success_data, 'status': success_code, 'success': True}

    def _request(self, method, url, data=None, wait=False):
        results = []
        if not self.threaded:
            for fairy in self.fairies:
                results.append(method(fairy, url, data=data))
        else:
            futures = []
            for fairy in self.fairies:
                futures.append(self.executor.submit(method, fairy, url, data=data))
            if wait:
                for future in futures:
                    results.append(future.result())
            else:
                self.futures.extend(futures)
                return True
        return self._aggregate(results)

    def add(self, fairy):
        """Add a cute little helper."""
        if isinstance(fairy, core.Session):
            self.fairies.append(fairy)
        else:
            self.fairies.append(core.Session(fairy, log_usage=not self.threaded,
                                             proxied=self.proxied))

    def get(self, url, wait=False):
        """Perform a GET request on the API."""
        return self._request(core.Session.get, url, wait=wait)

    def post(self, url, data=None, wait=False):
        """Perform a POST request on the API."""
        return self._request(core.Session.post, url, data=data, wait=wait)

    def vote(self, modelID, vote=0, gallery=None, wait=False):
        """Vote on a comment or gallery post."""
        VOTES = {-1: 'down', 0: 'veto', 1: 'up'}
        vote = VOTES.get(vote, vote)
        # Try to match a comment ID (full numerical)
        if gallery is None:
            gallery = isinstance(modelID, str) and re.match(r'^[0-9]{6,12}', modelID) is None
        url = f'{"gallery" if gallery else "comment"}/{modelID}/vote/{vote}'
        return self.post(url, wait=wait)

    def get_future_count(self):
        """Return current number of futures."""
        return len(self.futures)

    def get_future_done(self):
        """Return current number of finished futures."""
        return len([future for future in self.futures if future.done()])

    def get_future_running(self):
        """Return current number of running futures."""
        return len([future for future in self.futures if future.running()])

    def get_future_on_hold(self):
        """Return current number of waiting futures."""
        return len([future for future in self.futures
                    if not future.done() and not future.running()])

    def get_future_counts(self):
        """Return current numbers of futures in states."""
        return {'on_hold': self.get_future_on_hold(),
                'running': self.get_future_running(),
                'done':    self.get_future_done(),
                'total':   self.get_future_count()}
