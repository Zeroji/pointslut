"""Various utilities."""
import random
import re


MAX_DEPTH = 20


def _substitute(text):
    """Execute substitutions in a specific string."""
    left, right = len(text), 0
    while left >= 0:
        try:
            left = text.rindex('{', 0, left)
            # Jump to matching bracket (text.index isn't reliable in this case)
            right = left
            stack = 1
            while stack:
                right += 1
                if text[right] == '}':
                    stack -= 1
                elif text[right] == '{':
                    stack += 1
        except ValueError:
            return text
        if '|' in text[left:right]:
            text = text[:left] + random.choice(text[left+1:right].split('|')) + text[right+1:]
    return text


def _eval_to_string(value):
    """Evaluate a string from complex data."""
    if isinstance(value, dict):
        if 'o' in value:
            if random.random() * value['o'] < 1:
                return value['s']
            return ''
        return value.get('desc', value.get('s'))
    elif isinstance(value, str):
        return value
    elif isinstance(value, list):
        pool = []
        for item in value:
            pool.extend([item['s']] * item['w'])
        return random.choice(pool)
    return ''


def _get_value(key, src, depth=0, param=None):
    """Get a string value from complex data."""
    if depth >= MAX_DEPTH:
        return key
    value = src.get(key, key)

    # Evaluate substitutions and parameters
    line = _eval_to_string(value)
    line = _substitute(line)
    if '{x}' in line and param is not None:
        line = line.replace('{x}', param)

    # Evaluate references
    while True:
        match = re.search(r'\{(\w+)(\((\w+)\))?\}', line)
        if match is None:
            break
        param = None
        if match.group(2) is not None:
            param = _get_value(match.group(3), src, depth+1)
        replace = _get_value(match.group(1), src, depth+1, param)
        line = line[:match.start()] + replace + line[match.end():]
    return line


def get_value(key, src):
    """Get a string value from complex data."""
    line = _get_value(key, src)
    line = ' '.join(line.split())
    line = line.replace('<br>', '\n')
    return line
