class BtEncoder:
    def __init__(self):
        self.numbers1 = [14, 4, 3, 2, 1, 13, 8, 11, 6, 15, 12, 7, 10, 5, 0, 9]
        self.numbers2 = [10, 6, 13, 12, 14, 11, 1, 9, 15, 7, 0, 5, 3, 2, 4, 8]

    def hexStrToInt(self, hexStr):
        '''
        get a big hex string like "aa 00 aa 00 aa" and treat as little endian
        return list of int    
        '''
        return [int(hexStr[i:i+2], 16) for i in range(0, len(hexStr), 3)]

    def mod256(self, i):
        while i > 255:
            i -= 256
        while i < 0:
            i += 256
        return i

    def shuffle(self, dataNibble, nibbleCount, keyLeftNibbel, keyRightNibbel):
        i5 = self.mod256(nibbleCount >> 4)
        tmp1 = self.numbers1[self.mod256(dataNibble + nibbleCount + keyLeftNibbel) % 16]
        tmp2 = self.numbers2[self.mod256(tmp1 + keyRightNibbel + i5 - nibbleCount - keyLeftNibbel) % 16]
        tmp3 = self.numbers1[self.mod256(tmp2 + keyLeftNibbel + nibbleCount - keyRightNibbel - i5) % 16]
        return self.mod256(tmp3 - nibbleCount - keyLeftNibbel) % 16

    def encDecBytes(self, data, key):
        key = int(key, 16)
        result = []
        keyLeftNibbel = key >> 4
        keyRightNibbel = key & 15
        nibbelCount = 0
        for d in data:
            dataLeftNibbel = d >> 4
            dataRightNibbel = d & 15
            resultLeftNibbel = self.shuffle(dataLeftNibbel, nibbelCount, keyLeftNibbel, keyRightNibbel)
            resultRightNibbel = self.shuffle(dataRightNibbel, nibbelCount + 1, keyLeftNibbel, keyRightNibbel)
            result.append((resultLeftNibbel << 4) | resultRightNibbel)
            nibbelCount += 2
        return result
    def bruteforce_key(self, data):
        data = [int(d, 16) for d in data.split()]
        for key in range(0, 256):
            key = hex(key)[2:]
            if len(key) == 1:
                key = "0" + key
            result = self.encDecBytes(data, key)
            if result[0] == int(key, 16):
                print("key: " + key)
                print("result: " + str(result))
                return key
        return None

if __name__ == "__main__":
    # test
    bt = BtEncoder()
    key = "2a"
    data = ["2a 7F 80"]
    for data in data:
        data = [int(d, 16) for d in data.split()]
        # decode data with key
        decoded = bt.encDecBytes(data, key)
        # print decoded data
        print("".join([chr(d) for d in decoded[1:]]))
        # print as hex
        print("".join(["%02x" % d for d in decoded]))


