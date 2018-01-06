#!/usr/bin/env python
"""Repost whore."""
import logging
import random
import re
import sys
import core

PAGE_MIN = 100
PAGE_MAX = 1000
VOTE_RATIO = 10
FAIL_LIMIT = 3

FP_EDIT = re.compile(r'((\b.{,6}viral\s*|f.{,6}p.{,6})\bedit\b|'
                     r'\bedit\b.{,40}f.{,6}p|\*?edit[ *]{,2}:)',
                     re.IGNORECASE)
DESC = '\n\n( original post by {account_url}: {link} )'


def clean(text):
    """Remove FP edits and similar updates."""
    if not isinstance(text, str):
        return text
    match = re.search(FP_EDIT, text)
    if match is not None:
        text = text[:match.start()]
    return text


def repost(token):
    """Repost whore."""
    log = logging.getLogger()
    whore = core.Session(token)

    def reshare(post):
        """Repost an album and share the post."""
        post['description'] = clean(post['description'])

        def clean_image(image, _, success, album):
            """Clean up description and edit first image."""
            image['description'] = clean(image['description'])
            if success == 0:
                desc = image.get('description') or ''
                desc += DESC.format(**album)
                image['description'] = desc.strip()
            return image

        album = whore.upload_album(post, [clean_image])
        if not album:
            return False
        data = core.copy_keys(post, 'title', 'topic')
        if post['tags']:
            tags = [tag['name'] for tag in post['tags']]
            data['tags'] = ','.join(tags[:5])  # Imgur only allows 5 tags
        log.info('Sharing album %s to the gallery as %s', album, data['title'])
        req = whore.post('gallery/album/%s' % album, data=data)
        return req['success']

    page = random.randint(PAGE_MIN, PAGE_MAX)
    log.info('Fetching gallery from %d days ago', page)
    req = whore.get('gallery/hot/viral/%d' % page)
    if not req['success']:
        log.critical('Failed to get gallery page %d, aborting.', page)
        return
    gallery = req['data']
    gallery.sort(key=lambda post: post['points'], reverse=True)

    fails = 0
    for post in gallery:
        if post['ups'] < post['downs'] * VOTE_RATIO:
            continue
        if not post['is_album'] or post['is_ad']:
            continue
        if not post['tags']:
            continue
        if reshare(post):
            break
        fails += 1
        if fails >= FAIL_LIMIT:
            break


def main():
    """Call the repost whore."""
    if len(sys.argv) < 2:
        print('No token passed, aborting', file=sys.stderr)
        return
    repost(sys.argv[1])


if __name__ == '__main__':
    main()
