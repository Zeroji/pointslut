#!/usr/bin/env python
"""Refresh authentication tokens."""
import json
import sys
import requests


def refresh(token):
    """Refresh a single token."""
    data = requests.post('https://api.imgur.com/oauth2/token',
                         data={'refresh_token': token['refresh'],
                               'client_id': token['client_id'],
                               'client_secret': token['client_secret'],
                               'grant_type': 'refresh_token'}).json()
    token['token'] = data['access_token']
    token['refresh'] = data['refresh_token']
    return token


def main():
    """Refresh authentication tokens."""
    if len(sys.argv) < 2:
        print('No token file specified, aborting.', file=sys.stderr)
        return
    for file_name in sys.argv[1:]:
        with open(file_name, 'r') as token_file:
            data = json.load(token_file)
        if isinstance(data, list):
            for i, token in enumerate(data):
                data[i] = refresh(token)
            print('Refreshed %d tokens' % len(data))
        elif isinstance(data, dict):
            if 'token' in data and 'refresh' in data:
                data = refresh(data)
                print('Refreshed 1 token')
            else:
                for key, token in data.items():
                    data[key] = refresh(token)
                print('Refreshed %d tokens' % len(data))
        else:
            print('Unknown data structure, aborting.', file=sys.stderr)
            continue
        with open(file_name, 'w') as token_file:
            json.dump(data, token_file, indent=4)


if __name__ == '__main__':
    main()
