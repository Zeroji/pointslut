"""Cute little helpers."""
import configparser
import json
import logging
import os
import re
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

    def __init__(self, tokens=None, proxied=True):
        """Initialize with tokens."""
        self.fairies = []
        self.proxied = proxied
        if isinstance(tokens, str) and os.path.exists(tokens):
            with open(tokens, 'r') as tokens_file:
                tokens = json.load(tokens_file)
        if isinstance(tokens, dict):
            tokens = list(tokens.values())
        if isinstance(tokens, list):
            for token in tokens:
                self.fairies.append(core.Session(token, proxied=proxied))
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

    def add(self, fairy):
        """Add a cute little helper."""
        if isinstance(fairy, core.Session):
            self.fairies.append(fairy)
        else:
            self.fairies.append(core.Session(fairy, proxied=self.proxied))

    def get(self, url):
        """Perform a GET request on the API."""
        results = []
        for fairy in self.fairies:
            results.append(fairy.get(url))
        return self._aggregate(results)

    def post(self, url, data=None):
        """Perform a POST request on the API."""
        results = []
        for fairy in self.fairies:
            results.append(fairy.post(url, data=data))
        return self._aggregate(results)

    def vote(self, modelID, vote=0, gallery=None):
        """Vote on a comment or gallery post."""
        VOTES = {-1: 'down', 0: 'veto', 1: 'up'}
        vote = VOTES.get(vote, vote)
        # Try to match a comment ID (full numerical)
        if gallery is None:
            gallery = re.match(r'^[0-9]{6,12}', modelID) is None
        url = f'{"gallery" if gallery else "comment"}/{modelID}/vote/{vote}'
        return self.post(url)
