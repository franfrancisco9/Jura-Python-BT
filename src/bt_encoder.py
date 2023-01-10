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
    data = ["3b 98 f8 d6 88 80 d3 cb bf 23 70 22 a4 a8 c6 ab 46 f7 a6 24 0d 2c a6 be dc 7e cf 6d 28 41 18 6f 88 31 cd 65 ea 81 ef de 33 24 fa 0c 5d de fc 28 44 21 3e 23 15 2d 9a 14 e7 72 ed 1b 3f 65 13 bf 88 8d d1 6f ea 5a ef 6b 32 36 ae fc ed 94 a1 28 d4 4c 59 de 19 2c b9 f7 6c 33 68 bb 30 6f c8 9e b3 65 d5 6f 55 e5 d3 3a 1a 33 c2 c5 23 74 9c 1b a9 12 ac 51 71 1c 21 00 dc 6e d7 ed ea ef e4 1e 5c e1 dc 6d 88 9d ed de a3 29 fa 93 45 a3 fa e3 47 56 87 23 79 39 a2 99 33 7d 59 51 32 41 b9 6f ec b6 d1 65 c2 81 90 75 33 24 fa f4 a9 de fc ec 72 4c 3e 9e 15 8c de 14 e7 72 ed 1b 3f 65 13 bf 88 8d d1 6f ea 5a ef 6b"]
    #key = bt.bruteforce_key(data[0])
    key = "2a"
    for data in data:
        data = [int(d, 16) for d in data.split()]
        # decode data with key
        decoded = bt.encDecBytes(data, key)
        # print decoded data
        print("".join([chr(d) for d in decoded[1:]]))
        # print as hex
        print("".join(["%02x" % d for d in decoded]))


