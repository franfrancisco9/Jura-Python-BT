#!/usr/bin/env python3

import pexpect
import time
from bitarray import bitarray
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
import sys
import logging

# create logger in blue.log in current directory
logging.basicConfig(
    filename='blue.log',
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
# Define pin for buzzer
BuzzerPin = 7

def setupBuzzer(pin):
	global BuzzerPin
	BuzzerPin = pin
	GPIO.setmode(GPIO.BOARD)	# Numbers GPIOs by physical location
	GPIO.setup(BuzzerPin, GPIO.OUT)
	GPIO.output(BuzzerPin, GPIO.LOW)
	
def beep(duration):
    # Init buzzer
	setupBuzzer(BuzzerPin)
	GPIO.output(BuzzerPin, GPIO.HIGH)
	time.sleep(duration)
	GPIO.output(BuzzerPin, GPIO.LOW)



beep(0.5)

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
db = mdb.connect(host = "127.0.0.1", user = "root", passwd = os.getenv("PASSWD"), db = "AnnelieseDB")

# Initialize LCD
lcd = lcddriver.lcd()
lcd.lcd_clear()

# Function to get price of selected product
def get_price(product):
	price = float()
	c = db.cursor()
	db.commit()
	c.execute("SELECT SQL_NO_CACHE * FROM Produktliste WHERE Produkt = '" + product + "' ")
	for row in c.fetchall():
		price = row[2]
	c.close
	return price


priceCoffee = {
    "Americano":0.45,
    "Espresso":0.45,
    "Coffee":0.45,
    "Cappuccino":0.6,
    "Milkcoffee":0.6,
    "Espresso Macchiato":0.55,
    "Latte Macchiato":0.75,
    "Milk Foam":0.25,
    "Flat White":0.7
}

# update priceCoffee with function get_price
for key in priceCoffee:
    priceCoffee[key] = get_price(key)

print(priceCoffee)


PRODUCTS = {
    0:"Overall",
    1:"Americano",
    2:"Espresso",
    4:"Coffee",
    29:"Cappuccino",
    5:"Milkcoffee",
    6:"Espresso Macchiato",
    7:"Latte Macchiato",
    8:"Milk Foam",
    46:"Flat White"
}

in_machine_products  = {
    0:"Overall",
    1:"Americano",
    2:"Espresso",
    3:"Coffee",
    4:"Cappuccino",
    5:"Milkcoffee",
    6:"Espresso Macchiato",
    7:"Latte Macchiato",
    8:"Milk Foam",
    46:"Flat White"
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
    47: "SwitchOff Delay active", 48: "close front cover", 49: "left bean alert", 50: "right bean alert", 51: "cleaning",
    52: "cleaning finished", 53: "cleaning finished", 54: "cleaning finished", 55: "cleaning finished",
    56: "cleaning finished", 57: "cleaning finished", 58: "cleaning finished", 59: "cleaning finished",
}

def sleepTimer(secs):
	startTime = time.time()
	while (time.time() - startTime) < secs:
		pass

# define function that locks or unlocks the machine
def lockUnlockMachine(code, lock_status, unlock_code = "77e1"):
    child.sendline("char-write-req " + barista_mode_handle + " " + code)
    #print(child.readline())
    #print(child.readline())
    if code == unlock_code:
        lock_status = "unlocked"
    else:
        lock_status = "locked"
    return lock_status
      
# Function to get full name of given UID
def get_name(UID):
	c = db.cursor()
	db.commit()
	c.execute("SELECT SQL_NO_CACHE * FROM Benutzerverwaltung WHERE UID = " + UID + " ")
	for row in c.fetchall():
		name = row[2]
	c.close
	return name
	
# Function to get full name of given UID
def get_vorname(UID):
	c = db.cursor()
	db.commit()
	c.execute("SELECT SQL_NO_CACHE * FROM Benutzerverwaltung WHERE UID = " + UID + " ")
	for row in c.fetchall():
		vorname = row[3]
	c.close
	return vorname
	
# Function to get ID/chip number of given UID
def get_chip(UID):
	c = db.cursor()
	db.commit()
	c.execute("SELECT SQL_NO_CACHE * FROM Benutzerverwaltung WHERE UID = " + UID + " ")
	for row in c.fetchall():
		chip = row[0]
	c.close
	return chip

# Function to get value of given UID
def get_value(UID):
	value = float()
	c = db.cursor()
	db.commit()
	c.execute("SELECT SQL_NO_CACHE * FROM Benutzerverwaltung WHERE UID = " + UID + " ")
	for row in c.fetchall():
			value = row[4]
	c.close
	return value

# Function to set new value of given UID
def set_value(UID, value):
	c = db.cursor()
	c.execute("UPDATE Benutzerverwaltung SET Guthaben = " + str(value) + " WHERE UID = " + UID + " ")
	db.commit()
	c.close()


# Function to set insert new row into Kaufliste
def set_buylist(UID, product_name):
	chip = get_chip(UID)
	c = db.cursor()
	price = get_price(product_name)
	c.execute("INSERT INTO Kaufliste (ID, Chip, Produkt, Preis, Timestamp) VALUES (NULL, '" + str(chip) + "', '" + product_name + "', '" + str(price) + "', CURRENT_TIMESTAMP)")
	db.commit()
	c.close()

def readlineCR(port):
	rv = ""
	while True:
		ch = port.read()
		rv += ch
		if ch == '\r' or ch == '':
			return rv
#global RFIDREADER           
RFIDREADER = MFRC522.MFRC522()

def scanCard():
	#global RFIDREADER
    # Create an object of the class MFRC522
	#del(RFIDREADER)
	#RFIDREADER = MFRC522.MFRC522()
	RFIDREADER.MFRC522_Init()
	# Scan for cards    
	(status,TagType) = RFIDREADER.MFRC522_Request(RFIDREADER.PICC_REQIDL)

    # If a card is found
	if status == RFIDREADER.MI_OK:
		print("Card detected")
    
    # Get the UID of the card
	(status,uid) = RFIDREADER.MFRC522_Anticoll()

    # If we have the UID, continue
	if status == RFIDREADER.MI_OK:
		# Change UID to string
		uid_str =  str(uid[0]).zfill(3) + str(uid[1]).zfill(3) + str(uid[2]).zfill(3) + str(uid[3]).zfill(3)	
		return uid_str
	else:
		return "0"
# define function that locks or unlocks the machine

        
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


keep_alive_code, locking_code, unlock_code, KEY_DEC, all_statistics, initial_time, CURRENT_STATISTICS = setup(DEVICE, characteristics)

child = pexpect.spawn("gatttool -b " + DEVICE + " -I -t random")
# Connect to the device.
print("Connecting to ")
print(DEVICE)
child.sendline("connect")
print(child.child_fd)
#try:
child.expect("Connection successful", timeout=5)
print("Connected!")
logging.info("Connected")

child.sendline("char-write-cmd " + characteristics["statistics_command"][1] + " " + all_statistics)
time.sleep(1)
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
print("Statistics data: ", CURRENT_STATISTICS)
# Capture SIGINT for cleanup when the script is aborted
def end_read(signal,frame):
	global continue_reading
	beep(2)
	print("Ctrl+C captured, ending read.")
	inkasso = 0
	lcd.lcd_display_string("  Program over      ", 1)
	lcd.lcd_display_string("      ~~~~~~~~      ", 2)
	lcd.lcd_display_string("     Unlocking      ", 3)
	lcd.lcd_display_string("  -----> :( <-----  ", 4)
	time.sleep(3)
	lcd.lcd_clear()
	lcd.lcd_display_string("  Program not       ", 1)
	lcd.lcd_display_string("      ~~~~~~~~      ", 2)
	lcd.lcd_display_string("     Running        ", 3)
	lcd.lcd_display_string("  -----> :( <-----  ", 4)  
	db.close()
	continue_reading = False
	GPIO.cleanup()
	os.system("sudo ./backupMySQLdb.sh")
	print("Bakcup done!")
	logging.info("Backup done")
	logging.info("Program ended")
	_ = lockUnlockMachine(unlock_code, "locked")
	exit(0)

def read_statistics():
    try:
        product_made = False
        # write the all statistics command to statistics_command_handle
        child.sendline("char-write-req " + statistics_command_handle + " " + all_statistics)
        #print("All statistics sent!")
        time.sleep(1.2)
        # read the data from product progress handle
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
        #print("Statistics data: ", decoded)
        # change the values that are different from the previous ones when comparing with CURRENT_STATISTICS
        if decoded[0] != CURRENT_STATISTICS[0]:
            #lock_status = lockUnlockMachine(locking_code, lock_status)
            print("Overall products increased by 1")
            CURRENT_STATISTICS[0] = decoded[0]
            
        for i in range(1, len(decoded)):
            if decoded[i] != CURRENT_STATISTICS[i]:
                print("A " + PRODUCTS[i] + " was made!")
                product_made = PRODUCTS[i]
                print("Value changed to " + str(decoded[i]) + " from " + str(CURRENT_STATISTICS[i]))
                CURRENT_STATISTICS[i] = decoded[i]
        return product_made     
    except:
         print("Error reading statistics!")
         logging.error("Error reading statistics!")
         return False

# if no arguments assume that emegeny unlock is 0
if len(sys.argv) == 1:
    emergency_unlock = 0
else:
    emergency_unlock = int(sys.argv[1])
if emergency_unlock == 0:
    lock_status = "unlocked"
    lock_status = lockUnlockMachine(locking_code, lock_status)
    print("Machine locked!")
else:
    lock_status = "locked"
    lock_status = lockUnlockMachine(unlock_code, lock_status)
    print("Machine unlocked!")   
    exit()

# Hook the SIGINT
signal.signal(signal.SIGINT, end_read)


# Init buzzer
setupBuzzer(BuzzerPin)

while True:
    try:
        # Init Serial
        port = serial.Serial("/dev/serial0", baudrate = 9600, timeout = 1.0)
        print("Serial connection initialized")
        break
    except:
        print("Serial connection failed, ending program")
        logging.error("Serial connection failed, ending program")
        end_read(0,0)

lcd.lcd_display_string("   Machine Locked   ", 1)
lcd.lcd_display_string("      ~~~~~~~~      ", 2)
lcd.lcd_display_string(" Put tag to unlock  ", 3)
lcd.lcd_display_string("  -----> :) <-----  ", 4)
time.sleep(1)
beep(0.01)

port.flushInput()

buttonPress = False
continue_reading = True

# Welcome message
print("Welcome to the BlackBetty 2")
print("Press Ctrl-C to stop.")

lastSeen = ""
counter = 0
disp_init = 1
payment_to_date = 1
client_to_pay = ""
admin_locked = 0
admin_prod = 0
total_prod = 0
payed_prod = 0
#number = 0 

while continue_reading:
    #time.sleep(0.2)
    current_time = int(time.time() - initial_time)
    #print("Current time: " + str(current_time))
    # get hour of the day
    hour = int(time.strftime("%H"))
    minute = int(time.strftime("%M"))
    # print ("Hour: " + str(hour))
    # if current time is a multiple of 300 seconds then reset the bluetooth connection

    # if current_time % 30 == 0 and counter == 0:
    #     print("Resetting BT connection")
    #     beep(0.01)
    #     child.close()
    #     print(child.child_fd)
    #     print("Run gatttool...")
    #     child = pexpect.spawn("gatttool -b " + DEVICE + " -I -t random")
    #     print(child.child_fd)
    #     # Connect to the device.
    #     print("Connecting to ")
    #     print(DEVICE)
    #     child.sendline("connect")
    #     #try:
    #     child.expect("Connection successful", timeout=5)
    #     print("Connected!")
    #     #child, keep_alive_code, locking_code, unlock_code, KEY_DEC, all_statistics, initial_time, CURRENT_STATISTICS = setup(DEVICE, characteristics)
    #     #lock_status = lockUnlockMachine(locking_code, lock_status)
    if (hour == 1 or hour == 5) and minute == 30 :
        # reboot pi
        print("Rebooting pi")
        lcd.lcd_clear()
        os.system("sudo ./backupMySQLdb.sh")
        os.system("sudo reboot")
        logging.info("Rebooting pi")
        
    # if time elapsed is a multiple of 15 seconds then send keep alive code
    if current_time % 5 == 0:
        #print("Sending keep alive code")
        child.sendline("char-write-req " + heartbeat_handle + " " + keep_alive_code)
        #print(child.child_fd)
        #print(child.pid)
        data = child.readline()
        data += child.readline()
        print(b"Keep alive: " + data)
        # match substring Disconnected in data
        if "Disconnected" in str(data):
            # run setup
            print("Disconnected here")
            child.close()
            child = pexpect.spawn("gatttool -b " + DEVICE + " -I -t random")
            # Connect to the device.
            print("Connecting to ")
            print(DEVICE)
            child.sendline("connect")
            print(child.child_fd)
            #try:
            child.expect("Connection successful", timeout=5)
            print("Connected!")       
            lock_status = lockUnlockMachine(locking_code, lock_status)

    if disp_init == 1:
        lcd.lcd_clear()
        lcd.lcd_display_string("  Put Tag and then  ", 1)
        lcd.lcd_display_string("   Choose Product   ", 2)
        lcd.lcd_display_string("     In machine     ", 3)
        lcd.lcd_display_string("         :)         ", 4)
        disp_init = 0
        time.sleep(0.5)
        
    uid_str = scanCard() 
    GPIO.cleanup()

    if admin_locked == 1 and current_time % 10 == 0:
        prod = read_statistics()
        if prod != False:
            admin_prod += 1
            total_prod += 1
            set_buylist("0", prod)
            print("Admin made a product that was not payed for")

    if uid_str != "0":
        print("last seen: ", lastSeen)
        product_made = False
        if admin_locked == 0:
            lcd.lcd_clear()

        if (uid_str == mastercard1) or (uid_str == mastercard2):
            if lock_status == "locked":
                lock_status = lockUnlockMachine(unlock_code, lock_status)
                print("Machine unlocked permanently!")

                lcd.lcd_display_string("    Admin Unlock    ", 2)
                lcd.lcd_display_string("  -----> :) <-----  ", 3)
                admin_locked = 1
                 


            elif lock_status == "unlocked":
                lock_status = lockUnlockMachine(locking_code, lock_status)
                print("Machine locked!")
                lcd.lcd_display_string("    Admin Lock      ", 2)
                lcd.lcd_display_string("  -----> :( <-----  ", 3)
                disp_init = 1
                admin_locked = 0
                #number += 2
                #print("Number: ", number)
            time.sleep(1)
        
        elif admin_locked == 1:
            pass
        else:
            try:
                if lastSeen == "":
                    lastSeen = uid_str
                    value = get_value(uid_str)
                    if value < 0:
                         # alert user in lcd that they need to charge balance
                        lcd.lcd_clear()
                        lcd.lcd_display_string("  Your balance is   ", 1)
                        lcd.lcd_display_string("       < 0!         ", 2)
                        lcd.lcd_display_string("  Please charge it  ", 3)
                        lcd.lcd_display_string("  Locking Machine   ", 4)
                        beep(0.3)
                        time.sleep(0.5)
                        beep(0.3)
                        time.sleep(0.5)
                        beep(0.3)
                        time.sleep(2)
                        lock_status = lockUnlockMachine(locking_code, lock_status)                        
                        print("User balance is < 0")
                        lastSeen = ""
                        client_to_pay = ""
                        disp_init = 1


                    else:
                        value_str = str("Balance: " + str('%.2f' % value) + " EUR")
                        lastName = get_name(uid_str)
                        preName = get_vorname(uid_str)                
                        welStr = str("Hello " + preName)
                        msgStr3 = str("Hold for 2s please  ")
                        msgStr4 = str("Chip below          ")

                        lcd.lcd_display_string(welStr, 1)
                        lcd.lcd_display_string(value_str, 2)
                        lcd.lcd_display_string(msgStr3, 3)
                        lcd.lcd_display_string(msgStr4, 4)
                        time.sleep(1.5)
                    
                elif lastSeen == uid_str and product_made == False:
                    beep(0.05)
                    print("Opening coffe machine for choice")
                    lcd.lcd_clear()
                    lcd.lcd_display_string("    Select a        ", 1)
                    lcd.lcd_display_string("      product       ", 2)
                    lcd.lcd_display_string("  in the machine    ", 3)
                    lcd.lcd_display_string("  -----> :) <-----  ", 4)
                    lock_status = lockUnlockMachine(unlock_code, lock_status)
                    intial_time_2 = time.time()
                    chosen = 0
                    started = 0
                    over = 0
                    while over == 0:
                        #print("Waiting for product to be made")
                        time_total = int(time.time() - intial_time_2)
                        if time_total > 30 and started == 0:
                            #print("No product made in 25 seconds, locking machine")
                            lock_status = lockUnlockMachine(locking_code, lock_status)
                            lcd.lcd_display_string("    No Product      ", 1)
                            lcd.lcd_display_string("     selected       ", 2)
                            lcd.lcd_display_string("  Locking Machine   ", 3)
                            lcd.lcd_display_string("  -----> :( <-----  ", 4)
                            time.sleep(1.5)
                            #lcd.lcd_clear()
                            lastSeen = ""
                            disp_init = 1
                            chosen = 0
                            break
                        if int(time.time() - intial_time_2) % 5 == 0:
                            child.sendline("char-write-req " + heartbeat_handle + " " + keep_alive_code)
                        try:
                            # read the data from product progress handle
                            child.sendline("char-read-hnd " + product_progress_handle)
                            child.expect(": ")
                            data = child.readline()
                            data2 = [int(x, 16) for x in data.split()]
                            #print("Encoded: ", data)
                            data = [x for x in data.split()]
                            decoded = BtEncoder.encDecBytes(data2, KEY_DEC)
                            as_hex = ["%02x" % d for d in decoded]
                            #print("Decoded: ", as_hex)
                            #print("\nDecoded data as HEX: " + " ".join(["%02x" % d for d in decoded]))
                            if as_hex[1] not in ["3e", "00"] and time_total > 5 and started == 0:
                                #lock_status = lockUnlockMachine(locking_code, lock_status)
                                beep(0.5)
                                print("PRODUCT MADE")
                                client_to_pay = uid_str
                                lcd.lcd_clear()
                                preName = get_vorname(uid_str) 
                                print("as_hex[2]: ", as_hex[2])
                                product_made = in_machine_products[int(as_hex[2], 16)]
                                price_product = priceCoffee[product_made]
                                lcd.lcd_display_string(" " + product_made + " detected  ", 1)
                                lcd.lcd_display_string(" Will charge " + str(price_product), 2)
                                lcd.lcd_display_string(" " + preName + " ", 3)
                                lcd.lcd_display_string("  -----> :) <-----  ", 4)
                                time.sleep(1.5)
                                print("Product made was: ", product_made)
                                started = 1
                                disp_init = 1
                                chosen = 1
                                lock_status = lockUnlockMachine(locking_code, lock_status)
                                lastSeen = ""
                            elif started == 1 and as_hex[1] in ["3e", "00"]:
                                over = 1
                                print("Checking  costumer payment")
                                value_new = 0
                                if chosen == 1:    
                                    print("Setting value for uid: " + client_to_pay + " Name: " + preName)
                                    value_new = value - priceCoffee[product_made]
                                if value_new > 0 and chosen == 1:
                                    print("PAYING")
                                    # beep(0.05)
                                    # time.sleep(0.1)
                                    # beep(0.05)
                                    set_value(client_to_pay, value_new)
                                    payed_prod += 1
                                    total_prod += 1
                                    payment_to_date = 1
                                    preName = get_vorname(client_to_pay) 
                                    #beep(1)
                                    set_buylist(client_to_pay, product_made)
                                    lcd.lcd_clear()
                                    msgStr1 = str(product_made + " was made!")
                                    msgStr2 = str("  Happy betty :)  ")
                                    msgStr3 = str(" " + preName + " ")
                                    value_str = str("Balance: " + str('%.2f' % value_new) + " EUR")
                                    lcd.lcd_display_string(msgStr1, 1)
                                    lcd.lcd_display_string(msgStr2, 2)
                                    lcd.lcd_display_string(msgStr3, 3)
                                    lcd.lcd_display_string(value_str, 4)
                                    time.sleep(2)
                                    client_to_pay = ""
                                    counter = 0
                                    disp_init = 1
                                    product_made = False
                                elif value_new < 0 and chosen == 1:
                                    print("PAYING")
                                    lcd.lcd_clear()
                                    set_value(client_to_pay, value_new)
                                    payed_prod += 1
                                    total_prod += 1
                                    payment_to_date = 1
                                    #beep(1)
                                    set_buylist(client_to_pay, product_made)
                                    msgStr1 = str(product_made + " was made!")
                                    msgStr2 =   str(" Thank you!")
                                    msgStr3 =   str("Balance < 0!")
                                    value_str = str("Balance: " + str('%.2f' % value_new) + " EUR")
                                    lcd.lcd_display_string(msgStr1, 1)
                                    lcd.lcd_display_string(msgStr2, 2)
                                    lcd.lcd_display_string(msgStr2, 3)
                                    lcd.lcd_display_string(value_str, 4)
                                    time.sleep(2)
                                    client_to_pay = ""
                                    counter = 0
                                    disp_init = 1
                                    product_made = False
                                lcd.lcd_clear()
                                preName = get_vorname(uid_str) 
                                lcd.lcd_display_string("  Product Ended     ", 1)
                                lcd.lcd_display_string("      charged       ", 2)
                                lcd.lcd_display_string(" " + preName + " ", 3)
                                lcd.lcd_display_string("  -----> :) <-----  ", 4)
                                client_to_pay = ""
                                lastSeen = ""
                                time.sleep(2)
                            else:
                                continue

                        except Exception as e:
                            print("Error: " + str(e))
                            logging.error("Error: " + str(e))
                            try:
                                if e == b'\x1b[0mDisconnected':
                                    # run setup
                                    print("Disconnected")
                                    child.close()
                                    child = pexpect.spawn("gatttool -b " + DEVICE + " -I -t random")
                                    # Connect to the device.
                                    print("Connecting to ")
                                    print(DEVICE)
                                    child.sendline("connect")
                                    print(child.child_fd)
                                    #try:
                                    child.expect("Connection successful", timeout=5)
                                    print("Connected!")
                                    lock_status = lockUnlockMachine(locking_code, lock_status)
                            except:
                                pass
                            continue
            except Exception as e:
                print("The error raised is: ", e)
                logging.error("The error raised is: " + str(e))
                try:
                    if e == b'\x1b[0mDisconnected':
                        # run setup
                        print("Disconnected")
                        child.close()
                        child = pexpect.spawn("gatttool -b " + DEVICE + " -I -t random")
                        # Connect to the device.
                        print("Connecting to ")
                        print(DEVICE)
                        child.sendline("connect")
                        print(child.child_fd)
                        #try:
                        child.expect("Connection successful", timeout=5)
                        print("Connected!")
                        lock_status = lockUnlockMachine(locking_code, lock_status)
                except:
                    pass
                continue
    else:
        if lastSeen != "":
            counter = counter + 1
            #print(counter)
        if counter >= 10:
            lcd.lcd_clear()
            lastSeen = ""
            counter = 0
            beep(0.2)
            time.sleep(0.1)
            beep(0.2)

            msgStr1 = str("Chip removed?")
            msgStr3 = str("Product not chosen")
            msgStr4 = str("bye! :(")
            lcd.lcd_display_string(msgStr1, 1)
            lcd.lcd_display_string(msgStr3, 3)
            lcd.lcd_display_string(msgStr4, 4)
            sleepTimer(4)
            disp_init = 1
            client_to_pay = ""
            lastSeen = ""
            lock_status = lockUnlockMachine(locking_code, lock_status)
        sleepTimer(0.1)                
