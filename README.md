# NewSmile
## Another Smile Format Decoder/Encoder for Python 3

### Encoding ###
- Import SmileEncoder
```python 
from newsmile import SmileEncoder
```
- Create Encoder object, with arguments:
    - **raw_binary** (bool), default = **False**: contains binary data
    - **shared_values** (bool), default = **False**: maintains shared values buffer and references
    - **shared_keys** (bool), default = **True**: maintains shared keys buffer and references
    - **float_precision** (0|4|8), default = **0**: float values precisions (0=auto)
    - **encoding** (string), default = **'utf-8'**: encoding used for unicode values and keys

(Note: specs implies shared values are defaulted to False)
```python
encoder = SmileEncoder(shared_values=True)
```
- Encode data

If data is a dictionnary, it is encoded as is. If data is a string, it is considered as a json string.
```python
# Example with a dictionary
an_object = {'a': 123, 'b':[4, 5, 6], 'c':{'d': 'a_string', 'e':None}}
result = encoder.encode(an_object)
print(result)
```
```
>>> b':)\n\x03\xfa\x80a$\x03\xb6\x80b\xf8\xc8\xca\xcc\xf9\x80c\xfa\x80dGa_string\x80e!\xfb\xfb'
```
```python
# Example with json
import json
an_object = {'a': 123, 'b':[4, 5, 6], 'c':{'d': 'a_string', 'e':None}}
result = encoder.encode(json.dumps(an_object))
print(result)
```
```
>>> b':)\n\x03\xfa\x80a$\x03\xb6\x80b\xf8\xc8\xca\xcc\xf9\x80c\xfa\x80dGa_string\x80e!\xfb\xfb'
```

### Decoding ###
- Import SmileEncoder
```python 
from newsmile import SmileDecoder
```
- Create Decoder object, with arguments:
    - **encoding** (string), default = **'utf-8'**: encoding used for unicode values and keys
```python
decoder = SmileDecoder()
```
- Decode value
```python
decoder.decode(result)
decoded_object = decoder.decode(result)
print(decoded_object)
```
```
>>> {'a': 123, 'b': [4, 5, 6], 'c': {'d': 'a_string', 'e': None}}
```

### Encoding example, from file
```python
import json
from newsmile import SmileEncoder
encoder = SmileEncoder(shared_values=True, encoding='iso-8859-1')
dico = {'a': 1, 'b': [2, 3, 4], 'c': {'subkey': 'a string'}}
smile_data = encoder.encode(json.dumps(dico))
```

### Decoding example, from file
```python
from newsmile import SmileDecoder
decoder = SmileDecoder()
with open('smile-data-file', 'rb') as smile_file:
    data = decoder.decode(smile_file.read())
```

### Running tests
```bash
pytest
```
