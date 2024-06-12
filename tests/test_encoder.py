from newsmile import SmileDecoder
from newsmile import SmileEncoder


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


def test_encoder(json_path):
    decoder = SmileDecoder()
    encoder = SmileEncoder(shared_values=True, float_precision=4)
    smile_path = f'tests/data-test/smile/{json_path.stem}.smile'
    with open(json_path, 'r', encoding='utf-8') as json_file:
        encoded = encoder.encode(json_file.read())
    with open(smile_path, 'rb') as smile_file:
        from_smile = decoder.decode(smile_file.read())
    from_encoded = decoder.decode(encoded)

    assert ObjectComparator().compare(from_smile, from_encoded)