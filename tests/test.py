# -*- coding: utf-8 -*-
'''
Automatic tests for SmileDecoder and SmileEncoder
'''
import json
from pathlib import Path
from newsmile import SmileDecoder
from newsmile import SmileEncoder

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
        flag = True
        if isinstance(objecta, dict) and isinstance(objectb, dict):
            self._current = objecta, objectb
            for key in objecta.keys():
                if key in objectb:
                    flag = self.compare(objecta[key], objectb[key])
                    if not flag:
                        break
                else:
                    break
        elif isinstance(objecta, list) and isinstance(objectb, list):
            for idx, item in enumerate(objecta):
                if item in objectb:
                    flag = self.compare(objecta[idx], objectb[objectb.index(item)])
                    if not flag:
                        break
        else:
            if isinstance(objecta, float) and isinstance(objectb, float):
                flag = abs(objecta - objectb) < 2.220446049250313e-16
            else:
                flag = objecta == objectb
        return flag

if __name__ == '__main__':
    print('### Decoding Test ###')
    decoder = SmileDecoder()
    for smile_path in Path('data-test/smile').iterdir():
        json_path = f'data-test/json/{smile_path.stem}.jsn'
        with open(smile_path, 'rb') as smile_file:
            from_smile = decoder.decode(smile_file.read())
        with open(json_path, 'r', encoding='utf-8') as json_file:
            from_json = json.loads(json_file.read())
        RESULT = 'passed' if ObjectComparator().compare(from_smile, from_json) else 'failed'
        print(f"{smile_path.stem:20s}: {RESULT}")

    print('### Encoding Test ###')
    encoder = SmileEncoder(shared_values=True, float_precision=4)
    for json_path in Path('data-test/json').iterdir():
        smile_path = f'data-test/smile/{json_path.stem}.smile'
        with open(json_path, 'r', encoding='utf-8') as json_file:
            encoded = encoder.encode(json_file.read())
        with open(smile_path, 'rb') as smile_file:
            from_smile = decoder.decode(smile_file.read())
        from_encoded = decoder.decode(encoded)
        RESULT = 'passed' if ObjectComparator().compare(from_smile, from_encoded) else 'failed'
        print(f"{json_path.stem:20s}: {RESULT}")
