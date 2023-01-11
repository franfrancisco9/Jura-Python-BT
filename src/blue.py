import pexpect
import time
from bt_encoder import BtEncoder
from jura_encoder import JuraEncoder
from setup import setup
import os 
from dotenv import load_dotenv
from connection import *
import pymysql  
pymysql.install_as_MySQLdb()
import MySQLdb as mdb
import RPi.GPIO as GPIO
import lcddriver
import MFRC522
import signal
import time
import serial
from bitarray import bitarray



load_dotenv()

BtEncoder = BtEncoder()
JuraEncoder = JuraEncoder()

# BlackBetty2 mac address read from .env file
DEVICE = os.getenv("DEVICE")
print(DEVICE)

mastercard1 = os.getenv("MASTER_CARD_1")
mastercard2 = os.getenv("MASTER_CARD_2")
passwd = os.getenv("PASSWD")

# Open database connection
db = mdb.connect(host = "localhost", user = "root", passwd = os.getenv("passwd"), db = "AnnelieseDB")

# Initialize LCD
lcd = lcddriver.lcd()
lcd.lcd_clear()

priceCoffee = {
    "Ristretto":0.45,
	"Espresso":0.45,
    "Coffee":0.45,
    "Cappuccino":0.6,
    "Milkcoffee":0.6,
    "Espresso Macchiato":0.55,
    "Latte Macchiato":0.75,
    "Milk Foam":0.25,
    "Flat White":0.7
}

# Define pin for buzzer
BUZZER = 7

PRODUCTS = {
    0:"Overall",
    1:"Ristretto",
    2:"Espresso",
    3:"Coffee",
    4:"Cappuccino",
    5:"Milkcoffee",
    6:"Espresso Macchiato",
    7:"Latte Macchiato",
    8:"Milk Foam",
    9:"Flat White"
}

ALERTS = {
    0: "insert tray", 1: "fill water", 2: "empty grounds", 3: "empty tray", 4: "insert coffee bin",
    5: "outlet missing", 6: "rear cover missing", 7: "milk alert", 8: "fill system", 9: "system filling",
    10: "no beans", 11: "welcome", 12: "heating up", 13: "coffee ready", 14: "no milk (milk sensor)",
    15: "error milk (milk sensor)", 16: "no signal (milk sensor)", 17: "please wait", 18: "coffee rinsing",
    19: "ventilation closed", 20: "close powder cover", 21: "fill powder", 22: "system emptying",
    23: "not enough powder", 24: "remove water tank", 25: "press rinse", 26: "goodbye", 27: "periphery alert",
    28: "powder product", 29: "program-mode status", 30: "error status", 31: "enjoy product", 32: "filter alert",
    33: "decalc alert", 34: "cleaning alert", 35: "cappu rinse alert", 36: "energy safe", 37: "active RF filter",
    38: "RemoteScreen", 39: "LockedKeys", 40: "close tab", 41: "cappu clean alert", 42: "Info - cappu clean alert",
    43: "Info - coffee clean alert", 44: "Info - decalc alert", 45: "Info - filter used up alert", 46: "steam ready",
    47: "SwitchOff Delay active", 48: "close front cover", 49: "left bean alert", 50: "right bean alert"
}

# define function that locks or unlocks the machine
def lockUnlockMachine(code, lock_status):
    child.sendline("char-write-req " + barista_mode_handle + " " + code)
    print(child.readline())
    print(child.readline())
    if lock_status == "locked":
        lock_status = "unlocked"
    else:
        lock_status = "locked"
    return lock_status
        
# define function that receives decoded machine status and converts it to the corresponding alerts (if any)
# if corresponing bit is not set, the alert is not active
# remove key from the beggining
def getAlerts(status):
    # status comes like this: 2a 00 04 00 00 04 40 00 00 00 00 00 00 00 00 00 00 00 00 06
    # remove key from the beggining
    status = status[3:]
    #  bin(int('ff', base=16))[2:]
    status = [x for x in status.split()]
    # only use the first 13 bytes
    status = status[:13]
    status = [bin(int(byte,16))[2:]for byte in status]
    # divide each item in status into 8 bits
    status = [list(byte.zfill(8)) for byte in status]
    # print status
    # print(status)
    # combine into one string
    status = ''.join([item for sublist in status for item in sublist])
 
    # print("status: ", status)
    for i in range(len(status)):
        # if bit is set, print corresponding alert
        if status[i] == "1":
            print("Alert in bit " + str(i) + " with the alert " + ALERTS[i])

# Main Characteristic UUID and handle
machine_status = "5a401524-ab2e-2548-c435-08c300000710"
machine_status_handle = "0x000b"

barista_mode = "5a401530-ab2e-2548-c435-08c300000710"
barista_mode_handle = "0x0017"

product_progress = "5a401527-ab2e-2548-c435-08c300000710"
product_progress_handle = "0x001a"

heartbeat_uuid = "5a401529-ab2e-2548-c435-08c300000710"  # or p_mode
heartbeat_handle = "0x0011" 

heartbeat_read_uuid = "5a401538-ab2e-2548-c435-08c300000710" # or p_mode_read
heartbeat_read_handle = "0x0032"

start_product = "5a401525-ab2e-2548-c435-08c300000710"
start_product_handle = "0x000e"

statistics_command_uuid = "5A401533-ab2e-2548-c435-08c300000710"
statistics_command_handle = "0x0026"

statistics_data_uuid = "5A401534-ab2e-2548-c435-08c300000710"
statistics_data_handle = "0x0029"

uart_rx_uuid = "5a401624-ab2e-2548-c435-08c300000710"
uart_rx_hnd = "0x0036"

uart_tx_uuid = "5a401625-ab2e-2548-c435-08c300000710"
uart_tx_hnd = "0x0039"

# make dictionary with name: [uuid, handle]
characteristics = {
    "machine_status": [machine_status, machine_status_handle],
    "barista_mode": [barista_mode, barista_mode_handle],
    "product_progress": [product_progress, product_progress_handle],
    "heartbeat": [heartbeat_uuid, heartbeat_handle],
    "heartbeat_read": [heartbeat_read_uuid, heartbeat_read_handle],
    "start_product": [start_product, start_product_handle],
    "statistics_command": [statistics_command_uuid, statistics_command_handle],
    "statistics_data": [statistics_data_uuid, statistics_data_handle],
    "uart_tx": [uart_tx_uuid, uart_tx_hnd],
    "uart_rx": [uart_rx_uuid, uart_rx_hnd]
}


child, keep_alive_code, locking_code, unlock_code, KEY_DEC, all_statistics, initial_time, CURRENT_STATISTICS = setup(DEVICE, characteristics)
# lock_status = "unlocked"
# lock_status = lockUnlockMachine(locking_code, lock_status)
# print("Machine locked!")

# Hook the SIGINT
signal.signal(signal.SIGINT, end_read)

# Create an object of the class MFRC522
MIFAREReader = MFRC522.MFRC522()

# Init buzzer
setupBuzzer(BUZZER)

# Init Serial
port = serial.Serial("/dev/serial0", baudrate = 9600, timeout = 1.0)
print("Serial connection initialized")

lcd.lcd_display_string("   Machine Locked   ", 1)
lcd.lcd_display_string("      ~~~~~~~~      ", 2)
lcd.lcd_display_string(" Put tag to unlock  ", 3)
lcd.lcd_display_string("  -----> :) <-----  ", 4)
time.sleep(1)
beep(0.1)

port.flushInput()

buttonPress = False
continue_reading = True

# Welcome message
print("Welcome to the BlackBetty 2")
print("Press Ctrl-C to stop.")

lastSeen = ""
counter = 0
disp_init = 1

while continue_reading:
    # if time elapsed is a multiple of 15 seconds then send keep alive code
    if int(time.time() - initial_time) % 5 == 0:
        # print time in seconds since it was connected
        print("\nTime elapsed: " + str(int(time.time() - initial_time)))
        child.sendline("char-write-req " + heartbeat_handle + " " + keep_alive_code)
        print("Keep alive sent!") 

    if disp_init == 1:
        lcd.lcd_clear()
        lcd.lcd_display_string("  Put Tag and then  ", 1)
        lcd.lcd_display_string("   Choose Product   ", 2)
        lcd.lcd_display_string("     In machine     ", 3)
        lcd.lcd_display_string("         :)         ", 4)
        disp_init = 0
        time.sleep(0.5)

    uid_str = scanCard() 
    print("UID: " + uid_str)

    if lock_status == "unlocked":
        # write the all statistics command to statistics_command_handle
        child.sendline("char-write-req " + statistics_command_handle + " " + all_statistics)
        #print("All statistics sent!")
        time.sleep(1.2)
        # read the statistics data from statistics_data_handle
        child.sendline("char-read-hnd " + statistics_data_handle)
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
        # change the values that are different from the previous ones when comparing with CURRENT_STATISTICS
        for i in range(len(decoded)):
            if decoded[i] != CURRENT_STATISTICS[i]:
                if i != 0:
                    print("A " + PRODUCTS[i] + " was made!")
                else:
                    print("Overall products increased by 1")
                print("Value changed: " + str(decoded[i]) + " -> " + str(CURRENT_STATISTICS[i]))
                CURRENT_STATISTICS[i] = decoded[i]
        #print("Decoded statistics data: " + " ".join(["%02x" % d for d in decoded]))

    # Every 5 seconds read machine_status and decode them to hex using BtEncoder.encDecBytes
    # if int(time.time() - initial_time) % 5 == 0:
    #     key = "machine_status"
    #     print("\nCurrently reading: " + key)
    #     child.sendline("char-read-hnd " + characteristics[key][1])
    #     child.expect(": ")
    #     data = child.readline()
    #     print(b"Data: " + data)
    #     try: 
    #         data = [int(x, 16) for x in data.split()]
    #         decoded = BtEncoder.encDecBytes(data, KEY_DEC)
    #         #print("Decoded data as INT: " + str(decoded))
    #         # if key is machine_status, decode it to alerts
    #         if key == "machine_status":
    #             print("\nDecoded data as HEX: " + " ".join(["%02x" % d for d in decoded]))
    #             getAlerts(" ".join(["%02x" % d for d in decoded]))
    #     except:
    #         print("Error decoding data due to " + str(data))

