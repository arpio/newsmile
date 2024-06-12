# -*- coding: utf-8 -*-
'''
Automatic tests for SmileDecoder and SmileEncoder
'''
import json
from newsmile import SmileDecoder

# disable 'too few public methods' warning
# pylint: disable=R0903
class ObjectComparator:
    '''
    Utility class for compare two objects
    checks:
        if dictionaries have same keys and same values (recursive)
        if arrays contains same values
        if float values are the same (+/- eps)
    '''
    def __init__(self):
        self._current = None

    def compare(self, objecta, objectb):
        '''
        Main method for ObjectComparator class
        Args:
            objecta (any): first object to compare
            objectb (any): second object to compare
        '''
        equal = True
        if isinstance(objecta, dict) and isinstance(objectb, dict):
            self._current = objecta, objectb
            for key in objecta.keys():
                if key in objectb:
                    equal = self.compare(objecta[key], objectb[key])
                    if not equal:
                        break
                else:
                    return False
        elif isinstance(objecta, list) and isinstance(objectb, list):
            for idx, item in enumerate(objecta):
                if item in objectb:
                    equal = self.compare(objecta[idx], objectb[objectb.index(item)])
                    if not equal:
                        break
        else:
            if isinstance(objecta, float) and isinstance(objectb, float):
                equal = abs(objecta - objectb) < 2.220446049250313e-16
            else:
                equal = objecta == objectb
        return equal


def test_decoder(smile_path):
    decoder = SmileDecoder()
    json_path = f'tests/data-test/json/{smile_path.stem}.jsn'
    with open(smile_path, 'rb') as smile_file:
        from_smile = decoder.decode(smile_file.read())
    with open(json_path, 'r', encoding='utf-8') as json_file:
        from_json = json.loads(json_file.read())

    assert ObjectComparator().compare(from_smile, from_json)

