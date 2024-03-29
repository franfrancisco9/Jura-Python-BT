import pexpect
import time
from bt_encoder import BtEncoder
from jura_encoder import JuraEncoder
import logging
import os
logging.basicConfig(
    filename='blue.log',
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
##
# @file setup.py
#
# @brief In this file the connection to the Jura coffee machine is established.
#
#
# @section author_blue Author(s)
# - Created by Francisco Fonseca on 30/04/2023.
# 
#

## The instance of the BtEncoder class
BtEncoder = BtEncoder()
## The instance of the JuraEncoder class
JuraEncoder = JuraEncoder()
def setup(DEVICE, characteristics):
    '''!
    @brief This function is used to setup the connection to the Jura coffee machine.
    @param DEVICE The MAC address of the Jura coffee machine.
    @param characteristics A dictionary containing the characteristics of the Jura coffee machine.
    @return child, keep_alive_code, locking_code, unlock_code, KEY_DEC, all_statistics, initial_time, CURRENT_STATISTICS
    '''
    current_time = time.time()
    # send command gatttool -b ED:95:43:60:13:92 -I -t random to system with no output using pexpect
    # then send command connect to gatttool 
    # then send command char-write-cmd 0x0011 0e f7 2a to gatttool
    # gatttool -b ED:95:43:60:13:92 -I -t random
    # connect
    # char-write-req 0x0011 0e f7 2a
    while True:
        try:
            time.sleep(0.1)
            if time.time() - current_time > 180:
                logging.debug("Exiting and rebooting")
                os.system("sudo reboot")
                break
            print("Run gatttool...")
            child = pexpect.spawn("gatttool -b " + DEVICE + " -I -t random")
            # Connect to the device.
            print("Connecting to ")
            print(DEVICE)
            child.sendline("connect")
            #try:
            child.expect("Connection successful", timeout=5)
            print("Connected!")
            # print the time the connection was made
            initial_time = time.time()
            print("Initial time: " + str(initial_time))
            #time.sleep(5)
            # get current key
            child.sendline("char-read-hnd " + characteristics["machine_status"][1])
            child.expect(": ", timeout=5)
            data = child.readline().decode()
            print(data)
            KEY_DEC = BtEncoder.bruteforce_key(data)
            print("Key: ", KEY_DEC)
            data = [int(x, 16) for x in data.split()]
            decoded = BtEncoder.encDecBytes(data, KEY_DEC)
            print("\nDecoded data as HEX: " + " ".join(["%02x" % d for d in decoded]))
            keep_alive_code = KEY_DEC + " 7F 80"
            locking_code = KEY_DEC + " 01"
            unlock_code = KEY_DEC + " 00"
            all_statistics = KEY_DEC + " 00 10 FF FF"
            # encode keep alive code
            keep_alive_code = BtEncoder.encDecBytes([int(x, 16) for x in keep_alive_code.split()], KEY_DEC)
            keep_alive_code = "".join(["%02x" % d for d in keep_alive_code])
            locking_code = BtEncoder.encDecBytes([int(x, 16) for x in locking_code.split()], KEY_DEC)
            locking_code = "".join(["%02x" % d for d in locking_code])
            unlock_code = BtEncoder.encDecBytes([int(x, 16) for x in unlock_code.split()], KEY_DEC)
            unlock_code = "".join(["%02x" % d for d in unlock_code])
            all_statistics = BtEncoder.encDecBytes([int(x, 16) for x in all_statistics.split()], KEY_DEC)
            all_statistics = "".join(["%02x" % d for d in all_statistics])
            print("Keep alive code: " + keep_alive_code)
            print("Locking code: " + locking_code)
            print("Unlock code: " + unlock_code)
            print("All statistics: " + all_statistics)
            child.sendline("char-write-req " + characteristics["statistics_command"][1] + " " + all_statistics)
            time.sleep(1.5)
            child.sendline("char-read-hnd " + characteristics["statistics_data"][1])
            child.expect(": ")
            data = child.readline()
            #print(b"Statistics data: " + data)
            # decode the statistics data
            data = [int(x, 16) for x in data.split()]
            decoded = BtEncoder.encDecBytes(data, KEY_DEC)
            # join decoded data to a list for every three bytes example: [001200, 000000, 000098]
            decoded = ["".join(["%02x" % d for d in decoded[i:i+3]]) for i in range(0, len(decoded), 3)]
            # for every hex string in decoded list, convert to int
            decoded = [int(x, 16) for x in decoded]
            CURRENT_STATISTICS = decoded
            print("Current Statistics: " + str(decoded))
            return child, keep_alive_code, locking_code, unlock_code, KEY_DEC, all_statistics, initial_time, CURRENT_STATISTICS
        except:
            print("Failed to connect to device. Retrying...")
            logging.debug("Failed to connect to device at " + str(time.time()) + " Retrying...")
            continue
   