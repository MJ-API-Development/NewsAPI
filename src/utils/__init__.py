import string
import random

_char_set = string.ascii_lowercase + string.ascii_uppercase + string.digits


def create_id(size: int = 16, chars: str = _char_set) -> str:
    """
        **create_id**
            create a random unique id for use as indexes in Database Models

    :param size: size of string - leave as default if you can
    :param chars: character set to create Unique identifier from leave as default
    :return: uuid -> randomly generated id
    """
    # return ''.join(random.choice(chars) for _ in range(size))
    return ''.join(random.choices(chars, k=size))
