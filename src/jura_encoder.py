import sys
import time
import struct
import binascii
from bitarray import bitarray

class JuraEncoder:
    '''
    Class to encode and decode Jura protocol
    '''
    def __init__(self):
        # base layout for the bytes
        self.base_layout = bitarray('01011011')

    def tojura(self, letter, hex = 0):
        '''
        Convert a letter to the Jura protocol bytes
        If hex is set to 1, the output will be in hex
        '''
        if len(letter) != 1: raise ValueError('Needs a single byte')
        if hex: hex_code = ""
        c = bitarray(8)
        c.frombytes(letter)
        # make sure we only have 8 bits
        c = c[8:]
        # flip the nibbles bits
        c = c[2:4] + c[0:2] + c[6:8] + c[4:6]
        # flip the nibbles positions
        c = c[4:] + c[:4]
        # create layouts from base_layout
        bytes = [self.base_layout.copy() for i in range(4)]
        for i in range(4):
            # change the third and sixth bit
            bytes[i][2] = c[i * 2]
            bytes[i][5] = c[i * 2 + 1]
            if hex:
                # convert each bitarray to hex
                hex_code += binascii.hexlify(bytes[i]).decode() + " "

        return hex_code[:-1] if hex else bytes

    def fromjura(self, bytes, hex = 0):
        '''
        Convert Jura protocol bytes to a letter
        If hex is set to 1, the input will be in hex
        '''
        if hex:
            hex = bytes
            chars_hex_convert = []
            for j in hex.split():
                bit_array = bitarray('{0:b}'.format(ord(binascii.unhexlify(j))))
                if len(bit_array) < 8:
                    bit_array = bitarray('0' * (8 - len(bit_array))) + bit_array
                chars_hex_convert.append(bit_array)
            bytes = chars_hex_convert

        if len(bytes) != 4: raise ValueError('Needs an array of size 4')

        # create a bitarray from the bytes
        out = bitarray(8)
        out[0] = bytes[0][2]
        out[1] = bytes[0][5]
        out[2] = bytes[1][2]
        out[3] = bytes[1][5]
        out[4] = bytes[2][2]
        out[5] = bytes[2][5]
        out[6] = bytes[3][2]
        out[7] = bytes[3][5]
        
        # flip the nibbles positions	
        out = out[4:] + out[:4]
        # flip the nibbles bits
        out = out[2:4] + out[0:2] + out[6:8] + out[4:6]

        return out.tobytes()


def testencoder():
    '''
    Test the encoder
    '''
    jura = JuraEncoder()
    teststring = b'TY:\r\n' # enforce ascii
    bytes = []
    hex = []
    for c in teststring:
        bytes.append(jura.tojura(chr(c).encode()))
        hex.append(jura.tojura(chr(c).encode(), 1))
        
    print("Bytes:\n", bytes)
    print("Hex: ", hex)
    chars_bytes = b""
    chars_hex = b""
    for arr_hex in hex:
        chars_hex += jura.fromjura(arr_hex, 1)
    # 0F FF 11 FF FF 11 00 00
    # bytes = [[bitarray('00001111'), bitarray('11111111'), bitarray('00010001'), bitarray('11111111')],
    # [bitarray('11110001'), bitarray('00000000'), bitarray('00000000'), bitarray('00000000')]]
    for arr in bytes:
        chars_bytes += jura.fromjura(arr)

    print("chars_hex: ", chars_hex)
    print("chars_bytes: ", chars_bytes)
    assert chars_bytes == teststring, "encoding/decoding functions must be symmetrical"
    assert chars_hex == teststring, "encoding/decoding functions must be symmetrical"


if __name__ == "__main__":
    testencoder()

