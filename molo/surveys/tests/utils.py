import json
from itertools import izip_longest


def skip_logic_data(choices=list(), logics=list(), survey=None):
    data = [
        {'type': 'skip_logic', 'value': {
            'choice': choice,
            'skip_logic': logic,
            'survey': survey.id if choice == 'survey' else None,
        }} for choice, logic in izip_longest(choices, logics, fillvalue='next')
    ]
    return json.dumps(data)
