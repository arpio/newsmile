# -*- coding: utf-8 -*-
'''
SmileEncoder: encode an object to smile format
'''
import math
import json
import struct

# too few public methods: ACQ
# pylint: disable=R0903
# too many attributes: ACQ
# pylint: disable=R0902
class SmileEncoder:
    '''
    Smile encoding methods encapsulation
    '''
    # too many arguments: ACQ
    # pylint: disable=R0913
    def __init__(self,
        raw_binary=False,
        shared_values=False,
        shared_keys=True,
        float_precision=0,
        encoding='utf-8'):
        '''
        Args:
            raw_binary (bool): contains binary data
            shared_values (bool): maintains shared values buffer and references
            shared_keys (bool): maintains shared keys buffer and references
            single_or_double (0|4|8): float values precisions (0=auto)
            encoding (string): encoding used for unicode values and keys
        '''
        self._encoding = encoding
        # prepare header's bytes from parameters
        self._buffer = bytearray()
        self._raw_binary = raw_binary
        self._shared_values = shared_values
        self._shared_keys = shared_keys
        # 0: auto, 4: single, 8: double
        self._float_precision = float_precision
        self._shared_value_buffer = []
        self._shared_keys_buffer = []

    def encode(self, data):
        '''
        Start encoding: top-level function
        Args:
            data: dict: data to encode
                  string: json data string to encode
        '''
        if isinstance(data, str):
            object_to_encode = json.loads(data)
        else:
            object_to_encode = data
        # reinit buffers
        self._buffer = bytearray()
        self._shared_value_buffer = []
        self._shared_keys_buffer = []
        # write header
        self._set_header()
        if isinstance(object_to_encode, dict):
            self._encode_object(object_to_encode)
        elif isinstance(object_to_encode, list):
            self._encode_array(object_to_encode)
        else:
            self._encode_value(object_to_encode)
        return bytes(self._buffer)

    def _is_ascii(self, value):
        '''
        Check if string is ascii or unicode
        '''
        is_ascii, buffer = True, None
        # in_ascii = not (True in [ord(character) > 127 for character in value])
        for character in value:
            if ord(character) > 127:
                is_ascii = False
                break
        if is_ascii:
            buffer = value.encode('ascii')
        else:
            buffer = value.encode(self._encoding)
        return is_ascii, buffer

    @classmethod
    def _zigzag(cls, value, nbits=5):
        '''
        ZigZag encode value on nbits
        '''
        return (value >> (nbits - 1)) ^ (value << 1)

    def _set_header(self):
        '''
        Write header to buffer
        '''
        self._buffer.extend(':)\n\x00'.encode(self._encoding))
        if self._raw_binary:
            self._buffer[-1] |= 0x4
        if self._shared_values:
            self._buffer[-1] |= 0x2
        if self._shared_keys:
            self._buffer[-1] |= 0x1

    def _float_or_double(self, value):
        '''
        Check if value is single or double precision
        (dummy check: simply check if string representation
         ends with 000)
        '''
        if self._float_precision == 0:
            buf = f'{value:.15f}'[-3:] == '000'
            return 4 if buf else 8
        return self._float_precision

    def _encode_object(self, dico):
        '''
        Encode a dict
        '''
        if not isinstance(dico, dict):
            raise ValueError('Value should be a dictionnary')
        self._buffer.append(0xfa)
        for key in sorted(dico.keys()):
            self._encode_key(key)
            self._encode_value(dico[key])
        self._buffer.append(0xfb)

    def _encode_array(self, iterable):
        '''
        Encode an array (list or tuple)
        '''
        if not isinstance(iterable, (list, tuple)):
            raise ValueError('Value should be an iterable')
        self._buffer.append(0xf8)
        for value in iterable:
            self._encode_value(value)
        self._buffer.append(0xf9)

    def _encode_vint(self, value, nbits=None, zigzag=True):
        '''
        Variable length int encoding
        '''
        if zigzag and nbits:
            value = self._zigzag(value, nbits=nbits)
        buffer = [(value & 2**6-1) | 2**7]
        processed_bits = 6
        value >>= 6
        while value != 0 and (nbits is None or processed_bits < nbits):
            buffer.append(value & 2**7-1)
            value >>= 7
            processed_bits += 7
        self._buffer.extend(reversed(buffer))

    def _encode_int(self, value):
        '''
        Encoding integers
        '''
        if -16 <= value <= 15:
            self._buffer.append(0xc0 | self._zigzag(value, 5))
        elif -2 ** 31 <= value <= 2 ** 31 - 1:
            self._buffer.append(0x24)
            self._encode_vint(value, 32)
        elif -2 ** 63 <= value <= 2 ** 63 - 1:
            self._buffer.append(0x25)
            self._encode_vint(value, 64)
        else:
            # Big Integer
            bytes_count = math.ceil(value.bit_length() / 8)
            buffer = []
            shift = value.bit_length() - (value.bit_length() % 8 - 1)
            while shift > 0:
                buffer.append((value & (0x7f << shift)) >> shift)
                shift -= 7
            if shift != 0:
                buffer.append((value & 2 ** (7 + shift) - 1))
            self._buffer.append(0x26)
            self._encode_vint(bytes_count)
            self._buffer.extend(buffer)

    def _encode_float(self, value):
        '''
        Single or Double precision encoding
        '''
        nbytes = self._float_or_double(value)
        self._buffer.append({4: 0x28, 8: 0x29}[nbytes])
        buffer = struct.pack({4: '>f', 8: '>d'}[nbytes], value)
        buffer = struct.unpack({4: '>I', 8: '>Q'}[nbytes], buffer)[0]
        tmp_buf = []
        for _ in range({4: 5, 8: 10}[nbytes]):
            tmp_buf.append(buffer & 0x7f)
            buffer >>= 7
        self._buffer.extend(tmp_buf if nbytes == 4 else reversed(tmp_buf))

    def _encode_string_value(self, value):
        '''
        Encodage d'une valeur chaine
        '''
        if value == '':
            self._buffer.append(0x20)
            return
        is_ascii, buffer = self._is_ascii(value)
        if value in self._shared_value_buffer:
            # referenced value
            idx = self._shared_value_buffer.index(value)
            if idx < 31:
                # short index
                self._buffer.append(0x00 | (idx + 1 & 0x1f))
            else:
                # long index
                self._buffer.append(0xec | (idx & 0x300) >> 8)
                self._buffer.append(idx & 0xff)
        else:
            if len(buffer) <= (32 if is_ascii else 33):
                # tiny ascii or unicode
                self._buffer.append((0x40 if is_ascii else 0x80) |
                    (len(buffer) - (1 if is_ascii else 2)) & 0x1f)
                self._buffer.extend(buffer)
            elif len(buffer) <= (64 if is_ascii else 65):
                # short ascii or unicode
                self._buffer.append((0x60 if is_ascii else 0xa0) |
                    ((len(buffer) - (33 if is_ascii else 34)) & 0x1f))
                self._buffer.extend(buffer)
            elif len(buffer) > (64 if is_ascii else 65):
                # non referencable value
                self._buffer.append(0xe0 if is_ascii else 0xe4)
                self._buffer.extend(buffer)
                self._buffer.append(0xfc)
            if len(value) < 64 and self._shared_values:
                # cas d'une chaine elligible au buffer
                if len(self._shared_value_buffer) >= 1024:
                    self._shared_value_buffer = []
                self._shared_value_buffer.append(value)

    def _encode_string_key(self, key):
        '''
        Encoding a string key
        '''
        is_ascii, buffer = self._is_ascii(key)
        if key in self._shared_keys_buffer:
            # referenced key
            idx = self._shared_keys_buffer.index(key)
            if idx < 64:
                # short index
                self._buffer.append(0x40 | idx)
            else:
                # long index
                self._buffer.append(0x30 | idx >> 8)
                self._buffer.append(idx & 0xff)
        else:
            if len(buffer) <= 64:
                # fixed length string
                self._buffer.append((0x80 if is_ascii else 0xc0) | (len(key) - 1))
                self._buffer.extend(buffer)
            else:
                # variable length string
                self._buffer.append(0x34)
                self._buffer.extend(buffer)
                self._buffer.append(0xfc)
            if len(key) < 64 and self._shared_keys:
                # elligible string
                if len(self._shared_keys_buffer) >= 1024:
                    self._shared_keys_buffer = []
                self._shared_keys_buffer.append(key)

    def _encode_key(self, key):
        '''
        Top-level key encoding
        '''
        if isinstance(key, str):
            if key == "":
                # empty string
                self._buffer.append(0x20)
            else:
                self._encode_string_key(key)
        else:
            raise ValueError('Key case!')

    def _encode_value(self, value):
        '''
        Top-level value encoding
        '''
        if value == "":
            self._buffer.append(0x20)
        elif value is None:
            self._buffer.append(0x21)
        elif value is False:
            self._buffer.append(0x22)
        elif value is True:
            self._buffer.append(0x23)
        elif isinstance(value, int): # 0x20 -> 0x3f | 0xc0 -> 0xdf
            self._encode_int(value)
        elif isinstance(value, float):
            self._encode_float(value)
        elif isinstance(value, str): # 0x00 -> 0x1f / 0x40 -> 0xbf / 0xe0 -> 0xff
            self._encode_string_value(value)
        elif isinstance(value, dict):
            self._encode_object(value)
        elif isinstance(value, (list, tuple)):
            self._encode_array(value)
        else:
            raise ValueError('Value case!')
