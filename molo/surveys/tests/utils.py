import json
from itertools import izip_longest


def skip_logic_data(choices=list(), logics=list()):
    data = [
        {'type': 'skiplogic', 'value': {
            'choice': choice, 'skip_logic': logic
        }} for choice, logic in izip_longest(choices, logics, fillvalue='next')
    ]
    return json.dumps(data)
