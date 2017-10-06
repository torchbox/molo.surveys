import json
from itertools import izip_longest


def skip_logic_block_data(choice, logic, survey):
    return {
        'choice': choice,
        'skip_logic': logic,
        'survey': survey,
    }


def skip_logic_data(choices=list(), logics=list(), survey=None):
    data = [
        {'type': 'skip_logic', 'value': skip_logic_block_data(
            choice,
            logic,
            survey.id if choice == 'survey' else None,
        )
        } for choice, logic in izip_longest(choices, logics, fillvalue='next')
    ]
    return json.dumps(data)
