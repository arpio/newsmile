# -*- coding: utf-8 -*-
'''
SmileDecoder: decode smile dataformat input to python object
(dictionary, array or value)
Typical usage:
    from decoder import SmileDecoder
    with open(smile_path, 'rb') as smile_file:
            smile_contents = smile_file.read()
    decoder = SmileDecoder()
    decoded_data = decoder.decode(smile_contents)
'''
import struct

# too few public methods: ACQ
# pylint: disable=R0903
class SmileDecoder:
    '''
    Smile decoding methods
    '''
    def __init__(self, encoding='utf-8'):
        '''
        Class initialization
        Args:
            encoding (string): encoding used for decoding unicode strings
        '''
        self._properties = {
            'raw-binary': False,
            'shared-keys-names': False,
            'shared-string-values': True
        }
        self._encoding = encoding
        self._buffer = None
        self._current_obj = None
        self._index = 0
        self._shared_keys = []
        self._shared_values = []

    def _set_shared_key(self, key):
        '''
        Save shared key in dedicated buffer
        '''
        if len(key) <= 64:
            if len(self._shared_keys) >= 1024:
                self._shared_keys = []
            self._shared_keys.append(key)

    def _set_shared_value(self, value):
        '''
        Save shared value in dedicated buffer
        '''
        if len(value) <= 64:
            if len(self._shared_values) >= 1024:
                self._shared_values = []
            self._shared_values.append(value)

    @classmethod
    def _unzigzag(cls, value, mask = None):
        '''
        Unzigzag zigzag encoded int value
        '''
        if mask:
            value = value & mask
        return (value >> 1) ^ -(value & 1)

    def _float(self, bytes_count):
        '''
        Single or Double precision float decoding
        '''
        value = 0
        fmt = {4: '>f', 8: '>d'}[bytes_count]
        tokens = self._get_bytes(bytes_count + bytes_count // 4)
        for token in tokens if bytes_count == 8 else reversed(tokens):
            value <<= 7
            value |= token
        return struct.unpack(fmt, value.to_bytes(bytes_count, byteorder='big'))[0]

    def _int(self, unzigzag=True):
        '''
        Variable length int decoding
        '''
        value = 0
        token = self._get_bytes(1)[0]
        while token & 2**7 == 0:
            value <<= 7
            value |= token & 2**7-1
            token = self._get_bytes(1)[0]
        value <<= 6
        value |= token & 2**6-1
        return self._unzigzag(value, None) if unzigzag else value

    def _bigint(self):
        '''
        Big integer decoding
        '''
        length = self._int(unzigzag=False)
        remain = 8 * length % 7
        bytes_count = int((8 * length - remain)/7)
        value = 0
        tokens = self._get_bytes(bytes_count)
        for token in tokens:
            value <<= 7
            value |= token
        if remain > 0:
            value <<= remain
            value |= self._get_bytes(1)[0] & 0x7f
        return value

    def _string(self, token_type, length, encoding):
        '''
        String decoding
        '''
        if length:
            # fixed length string
            buffer = self._get_bytes(length).decode(encoding)
            if token_type == 'value':
                self._set_shared_value(buffer)
            elif token_type == 'key':
                self._set_shared_key(buffer)
        else:
            # Variable length string
            buffer = bytearray()
            token = self._get_bytes(1)[0]
            while token != 0xfc:
                buffer.append(token)
                token = self._get_bytes(1)[0]
            buffer = buffer.decode(encoding)
        return buffer

    def _get_bytes(self, count):
        '''
        Get bytes from buffer and increase index
        '''
        buffer = self._buffer[self._index: self._index + count]
        self._index += count
        return buffer

    def _decode_object(self):
        '''
        Entry point for decoding dictionary
        '''
        obj = {}
        while self._buffer[self._index] != 0xfb:
            key = self._decode_key()
            value = self._decode_value()
            obj[key] = value
        self._index += 1
        return dict(sorted(obj.items()))

    def _decode_array(self):
        '''
        Entry point for decoding array
        '''
        array = []
        while self._buffer[self._index] != 0xf9:
            value = self._decode_value()
            array.append(value)
        self._index += 1
        return array

    def _get_referenced(self, token_type, reference):
        '''
        Retrieve referenced key or value in buffer
        '''
        if (token_type == 'value' and not self._properties['shared-string-values']) or \
            (token_type == 'key' and not self._properties['shared-keys-names']):
            raise ValueError(f'Shared References not setted for {token_type}s')
        if token_type == 'value':
            referenced =  self._shared_values[reference]
        else:
            referenced =  self._shared_keys[reference]
        return referenced

    def _decode_value(self):
        '''
        Decoding a value (dispatch for int, float, string, array or dict)
        '''
        value = None
        token = self._get_bytes(1)[0]
        if 0x00 <= token <= 0x1f:
            # Short value String Reference
            value = self._get_referenced('value', token - 1)
        elif 0x20 <= token <= 0x23:
            # Special values: empty string, None, False, True
            value = {0x20: "", 0x21: None, 0x22: False, 0x23: True}[token]
        elif 0x24 <= token <= 0x25:
            # Integer
            value = self._int()
        elif token == 0x26:
            # Big Integer
            value = self._bigint()
        elif token == 0x27:
            # Unused -> Exception
            raise ValueError(f'Value : {token:02x}:  reserved for future use')
        elif token == 0x28:
            # Float (32 bits)
            value = self._float(4)
        elif token == 0x29:
            # Double (64 bits)
            value = self._float(8)
        elif 0x40 <= token <= 0x5f:
            # Tiny ASCII
            value = self._string('value', (token & 2**5-1) + 1, 'ascii')
        elif 0x60 <= token <= 0x7f:
            # Short ASCII
            value = self._string('value', (token & 2**5-1) + 33, 'ascii')
        elif 0x80 <= token <= 0x9f:
            # Tiny UNICODE
            value = self._string('value', (token & 2**5-1) + 2, self._encoding)
        elif 0xa0 <= token <= 0xbf:
            # Short UNICODE
            value = self._string('value', (token & 2**5-1) + 34, self._encoding)
        elif 0xc0 <= token <= 0xdf:
            # Small Integer
            value = SmileDecoder._unzigzag(token, 2**5-1)
        elif token == 0xe0:
            # Non referencable ASCII text
            value = self._string('value', None, 'ascii')
        elif token == 0xe4:
            # Non referencable UNICODE text
            value = self._string('value', None, self._encoding)
        elif 0xec <= token < 0xf0:
            # Long value String Reference
            value = self._get_referenced('value', (token & 0x3) << 8 | self._get_bytes(1)[0])
        elif token == 0xfa:
            # Sub Object
            value = self._decode_object()
        elif token == 0xf8:
            # Sub Array
            value = self._decode_array()
        elif token == 0xfd:
            # binary (raw)
            length = self._int(False)
            value = self._get_bytes(length)
        else:
            raise ValueError(f'value: {token:02x}: unknown token')
        return value

    def _decode_key(self):
        '''
        Decoding dict key
        '''
        key = None
        token = self._get_bytes(1)[0]
        # reserved
        if (0 <= token <= 0x1f) or \
            (0x21 <= token <= 0x2f):
            raise ValueError(f'key: {self._buffer[self._index]:02x}: reserved for future use')
        # empty string
        elif token == 0x20:
            key = ""
        # Long Shared Key Name Reference
        elif 0x30 <= token <= 0x33:
            key = self._get_referenced('key', (token & 0b11) << 8 | self._get_bytes(1)[0])
        elif token == 0x34:
        # Long NOT Shared Unicode Key Name
            self._string('key', None, self._encoding)
        # Short Shared Key Name Reference
        elif 0x40 <= token <= 0x7F:
            key = self._get_referenced('key', token - 0x40)
        # Short ASCII Name
        elif 0x80 <= token <= 0xBF:
            key = self._string('key', token - 0x80 + 1, 'ascii')
        # Short unicode name
        elif 0xC0 <= token <= 0xf7:
            key = self._string('key', token - 0xc0 + 2, self._encoding)
        else:
            raise ValueError(f'key error: {self._buffer[self._index]:02x}')
        return key

    def _decode_header(self):
        '''
        Decoding header
        '''
        buffer = self._get_bytes(4)
        if buffer[:3].decode(self._encoding) != ':)\n':
            raise ValueError('invalid header')
        self._properties['raw-binary'] = buffer[3] & 4 > 0
        self._properties['shared-keys-names'] = buffer[3] & 2 > 0
        self._properties['shared-string-values'] = buffer[3] & 1 > 0

    def decode(self, buffer):
        '''
        Class main entry point
        Args:
            buffer (bytes | bytearray | list of bytes): smile data to decode
        Typical usage:
            with open(smile_path, 'rb') as smile_file:
                smile_contents = smile_file.read()
            decoder = SmileDecoder()
            decoded_data = decoder.decode(smile_contents)
        '''
        self._index = 0
        self._shared_keys = []
        self._shared_values = []
        if not isinstance(buffer, (bytes, bytearray)):
            self._buffer = bytes([ord(byte) for byte in buffer])
        else:
            self._buffer = buffer
        self._decode_header()
        return self._decode_value()
