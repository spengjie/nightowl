"""
Author: Ben Hoyt @ http://code.activestate.com/recipes/users/4170919/
Reference URL:
http://code.activestate.com/recipes/577781-pluralize-word-convert-singular-word-to-its-plural/
"""

import re


ABERRANT_PLURAL_MAP = {
    'appendix': 'appendices',
    'barracks': 'barracks',
    'biro': 'biros',
    'cactus': 'cacti',
    'child': 'children',
    'criterion': 'criteria',
    'deer': 'deer',
    'dynamo': 'dynamos',
    'elf': 'elves',
    'focus': 'foci',
    'foot': 'feet',
    'fungus': 'fungi',
    'goose': 'geese',
    'hoof': 'hooves',
    'index': 'indices',
    'kimono': 'kimonos',
    'man': 'men',
    'mouse': 'mice',
    'nucleus': 'nuclei',
    'ox': 'oxen',
    'person': 'people',
    'phenomenon': 'phenomena',
    'photo': 'photos',
    'piano': 'pianos',
    'sheep': 'sheep',
    'syllabus': 'syllabi',
    'tooth': 'teeth',
    'woman': 'women',
    'Chinese': 'Chinese',
    'Japanese': 'Japanese',
}
VOWELS = set('aeiou')


def pluralize(singular):
    """Return plural form of given lowercase singular word (English only). Based on
    ActiveState recipe http://code.activestate.com/recipes/413172/

    >>> pluralize('')
    ''
    >>> pluralize('goose')
    'geese'
    >>> pluralize('dolly')
    'dollies'
    >>> pluralize('genius')
    'genii'
    >>> pluralize('jones')
    'joneses'
    >>> pluralize('pass')
    'passes'
    >>> pluralize('zero')
    'zeros'
    >>> pluralize('casino')
    'casinos'
    >>> pluralize('hero')
    'heroes'
    >>> pluralize('church')
    'churches'
    >>> pluralize('car')
    'cars'

    """
    if not singular:
        return ''
    plural = ABERRANT_PLURAL_MAP.get(singular)
    if plural:
        return plural
    root = singular
    try:
        if singular[-1] == 's':
            if singular[-2] in VOWELS:
                if singular[-3:] == 'ius':
                    root = singular[:-2]
                    suffix = 'i'
                else:
                    root = singular[:-1]
                    suffix = 'ses'
            else:
                suffix = 'es'
        elif singular[-1] == 'x':
            suffix = 'es'
        elif singular[-2:] in ('ch', 'sh'):
            suffix = 'es'
        elif singular[-1] == 'y' and singular[-2] not in VOWELS:
            root = singular[:-1]
            suffix = 'ies'
        elif singular[-1] == 'o':
            if singular[-2] in VOWELS:
                suffix = 's'
            else:
                suffix = 'es'
        elif singular[-1] == 'f':
            root = singular[:-1]
            suffix = 'ves'
        elif singular[-2:] == 'fe':
            root = singular[:-2]
            suffix = 'ves'
        else:
            suffix = 's'
    except IndexError:
        suffix = 's'
    return root + suffix


def analyze(text):
    return re.sub(r'(\S+)([A-Z][a-z])', r'\1 \2', text)
