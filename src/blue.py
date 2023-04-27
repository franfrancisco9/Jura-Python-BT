#!/usr/bin/env python3

##
# @mainpage Jura-Python-BT Documentation
#
# @section description_main Description
# This is the documentation for the Jura-Python-BT project.
# The documentations focus on the main script blue.py.
# The projects consists of a Raspberry Pi 3B+ that communicates with a Jura coffee machine via Bluetooth.
# Additionally, the Raspberry Pi communicates with a database, a LCD display and a RFID reader.
# This is all used to create a coffee machine that can be used by multiple users, where each user has a specific RFID tag.
# This way the machine can be locked until a user scans his/her RFID tag.
# The user can then choose a coffee and will be charged for it from the database.
#

##
# @file blue.py
#
# @brief Main script to run for BlackBetty.
#
#
# @section author_blue Author(s)
# - Created by Francisco Fonseca on 25/04/2023.
# 
#

# Imports
import pexpect
import time
from bt_encoder import BtEncoder
from jura_encoder import JuraEncoder
from setup import setup
import os 
from dotenv import load_dotenv
from database import db_connect, getUID_stats, get_name, get_price, get_vorname, get_chip, get_value, set_value, set_buylist
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
import json

## Global Constants
## The dictionary of UUIDs and handles of the bluetooth characteristics
CHARACTERISTICS = json.load(open("/home/pi/Jura-Python-BT/data/uuids_handles.json"))["characteristics"]
## The dictionary of alerts from machine status
ALERTS = json.load(open("/home/pi/Jura-Python-BT/data/alerts.json"))["alerts"]
## The dictionary of products the machine can make
PRODUCTS = json.load(open("/home/pi/Jura-Python-BT/data/products.json"))["products"]
## The dictionary of prices of the products
PRICECOFFEE = json.load(open("/home/pi/Jura-Python-BT/data/prices.json"))["pricecoffee"]
## The pin for the buzzer
BUZZER_PIN = 7
## Load the environment variables from .env file
load_dotenv()
## The BlackBetty2 mac address read from .env file
DEVICE = os.getenv("DEVICE")
## The UID of master card 1 read from .env file
MASTERCARD1 = os.getenv("MASTER_CARD_1")
## The UID of master card 2 read from .env file
MASTERCARD2 = os.getenv("MASTER_CARD_2")
## The open database connection
DB = db_connect()
## The instance of the BtEncoder class
BtEncoder = BtEncoder()
## The instance of the JuraEncoder class
JuraEncoder = JuraEncoder()
## The instance of the RFID reader class           
RFIDREADER = MFRC522.MFRC522()

# create logger in blue.log in current directory
logging.basicConfig(
    filename='blue.log',
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

def setupBuzzer(pin):
	'''!
	Setup buzzer
	@param pin The pin number of the buzzer.
	'''
	global BUZZER_PIN
	BUZZER_PIN = pin
	GPIO.setmode(GPIO.BOARD)	# Numbers GPIOs by physical location
	GPIO.setup(BUZZER_PIN, GPIO.OUT)
	GPIO.output(BUZZER_PIN, GPIO.LOW)
	
def beep(duration):
	'''!
	Make a beep sound
	@param duration The time in ms of the beep.
	'''
    # Init buzzer
	# setupBuzzer(BUZZER_PIN)
	# GPIO.output(BUZZER_PIN, GPIO.HIGH)
	# time.sleep(duration)
	# GPIO.output(BUZZER_PIN, GPIO.LOW)
	print("beep off")

beep(0.5)

## Initialize LCD
lcd = lcddriver.lcd()
lcd.lcd_clear()  
lcd.lcd_display_string("  Starting Program  ", 1)
lcd.lcd_display_string("     Connecting     ", 2)
lcd.lcd_display_string("     Please wait!   ", 3)
lcd.lcd_display_string("  -----> :) <-----  ", 4)

# update PRICECOFFEE with function get_price
for key in PRICECOFFEE:
    PRICECOFFEE[key] = get_price(DB, key)

def lockUnlockMachine(code, lock_status, unlock_code = "77e1"):
    '''!
    Lock or unlock the machine
    @param code The code to unlock the machine.
    @param lock_status The current status of the machine.
    @param unlock_code The code to unlock the machine (default 77e1).

    @return lock_status The new status of the machine ("locked" or "unlocked")
    '''
    child.sendline("char-write-req " + CHARACTERISTICS["barista_mode"][1] + " " + code)

    if code == unlock_code:
        lock_status = "unlocked"
    else:
        lock_status = "locked"

    return lock_status

# define function that scans for RFID card
def scanCard(): 
	'''!
	Scan for RFID tag
    @return uid_str The UID of the tag or "0" if no tag is found
	'''
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
      
def getAlerts(status):
    '''!
    Get alerts from the decoded machine status and convert it to the corresponding alerts (if any)
    If the corresponding bit is not set, the alert is not active
    @param status: machine status
    @return list of alerts according to ..data/alerts.json
    '''
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
    # combine into one string
    status = ''.join([item for sublist in status for item in sublist])
 
    # print("status: ", status)
    for i in range(len(status)):
        # if bit is set, print corresponding alert
        if status[i] == "1":
            print("Alert in bit " + str(i) + " with the alert " + ALERTS[str(i)])

## Get all necessary variables from setup.py -> check file for more information
child, keep_alive_code, locking_code, unlock_code, KEY_DEC, all_statistics, initial_time, CURRENT_STATISTICS = setup(DEVICE, CHARACTERISTICS)


if int(getUID_stats(DB)) < CURRENT_STATISTICS[0]:
    # change the UID in the database Benutzerverwaltung to CURRENT_STATISTICS[0] where id = 1000
    # this ensures the current number of coffees made by the machine is in the database
    print("updating the value in the table")
    c = DB.cursor()
    c.execute("UPDATE Benutzerverwaltung SET UID = " + str(CURRENT_STATISTICS[0]) + " WHERE id = 1000;")	
    DB.commit()
    c.close()

# function that runs if ctrl+c is pressed
def end_read(signal,frame):
	'''!
	End the program
	Runs when Ctrl+C is pressed
	'''
	global continue_reading
	beep(2)
	print("Ctrl+C captured, ending read.")
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
	continue_reading = False
	GPIO.cleanup()
	os.system("cd /home/pi/Jura-Python-BT/src/ && sudo ./backupMySQLdb.sh")
	print("Bakcup done!")
	logging.info("Backup done")
	logging.info("Program ended")
	child.sendline("char-write-req " + CHARACTERISTICS["statistics_command"][1] + " " + all_statistics)
	time.sleep(1.5)
	child.sendline("char-read-hnd " + CHARACTERISTICS["statistics_data"][1])
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
	if int(getUID_stats(DB)) < CURRENT_STATISTICS[0]:
		# change the UID in the database Benutzerverwaltung to CURRENT_STATISTICS[0] where id = 1000
		print("updating the value in the table from", getUID_stats(DB), "to", CURRENT_STATISTICS[0])
		c = DB.cursor()
		c.execute("UPDATE Benutzerverwaltung SET UID = " + str(CURRENT_STATISTICS[0]) + " WHERE id = 1000;")	
		DB.commit()
		c.close()
	DB.close()
	_ = lockUnlockMachine(unlock_code, "locked")
	exit(0)

# function that reads the statistics from the machine
def read_statistics():
    '''!
    Read the statistics from the machine
    @return list of statistics
    '''
    try:
        product_made = False
        # write the all statistics command to statistics_command_handle
        child.sendline("char-write-cmd " + CHARACTERISTICS["statistics_command"][1] + " " + all_statistics)
        #print("All statistics sent!")
        time.sleep(1.5)
        # read the data from product progress handle
        # read the statistics data from statistics_data_handle
        child.sendline("char-read-hnd " + CHARACTERISTICS["statistics_data"][1])
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
                print("A " + PRODUCTS[str(i)] + " was made!")
                product_made = PRODUCTS[str(i)]
                print("Value changed to " + str(decoded[i]) + " from " + str(CURRENT_STATISTICS[i]))
                CURRENT_STATISTICS[i] = decoded[i]
        if int(getUID_stats(DB)) < CURRENT_STATISTICS[0]:
            # change the UID in the database Benutzerverwaltung to CURRENT_STATISTICS[0] where id = 1000
            print("updating the value in the table from", getUID_stats(DB), "to", CURRENT_STATISTICS[0])
            c = DB.cursor()
            c.execute("UPDATE Benutzerverwaltung SET UID = " + str(CURRENT_STATISTICS[0]) + " WHERE id = 1000;")	
            DB.commit()
            c.close()
        return product_made     
    except Exception as e:
         print("Error reading statistics!")
         logging.error("Error reading statistics " + str(e))
         return False

# if no arguments assume that emergency unlock is 0
# if emergency unlock is 0, lock the machine
# if emergency unlock is 1, unlock the machine
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

# Hook the SIGINT to end_read function (ctrl + c)
signal.signal(signal.SIGINT, end_read)

# Init buzzer
setupBuzzer(BUZZER_PIN)

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

# Welcome message
print("Welcome to the BlackBetty 2")
print("Press Ctrl-C to stop.")

port.flushInput()

buttonPress = False
continue_reading = True
lastSeen = ""
counter = 0
disp_init = 1
payment_to_date = 1
client_to_pay = ""
admin_locked = 0 
''' 1 = unlocked, 0 = locked '''
admin_prod = 0
total_prod = 0
payed_prod = 0
#number = 0 

time.sleep(1)
while continue_reading:
    '''
    Main loop
    In this loop the program makes sure the connection is alive and the machine is locked
    Scans for tags
    If a tag is found, it unlocks the machine and waits for a product to be made
    If a product is made, it locks the machine again and charges the user
    '''
    #time.sleep(0.2)
    current_time = int(time.time() - initial_time)
    #print("Current time: " + str(current_time))
    # get hour of the day
    hour = int(time.strftime("%H"))
    minute = int(time.strftime("%M"))
    second = int(time.strftime("%S"))
    if (hour == 17 and minute == 0 and second == 0):
        os.system("cd /home/pi/Jura-Python-BT/src/ && sudo ./backupMySQLdb.sh")
    if (hour == 1 or hour == 5) and minute == 30 :
        # reboot pi
        child.sendline("char-write-req " + CHARACTERISTICS["statistics_command"][1] + " " + all_statistics)
        time.sleep(1.5)
        child.sendline("char-read-hnd " + CHARACTERISTICS["statistics_data"][1])
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
        if int(getUID_stats(DB)) < CURRENT_STATISTICS[0]:
            # change the UID in the database Benutzerverwaltung to CURRENT_STATISTICS[0] where id = 1000
            print("updating the value in the table")
            c = DB.cursor()
            c.execute("UPDATE Benutzerverwaltung SET UID = " + str(CURRENT_STATISTICS[0]) + " WHERE id = 1000;")
            DB.commit()
            c.close()
        print("Rebooting pi")
        lcd.lcd_clear()
        os.system("cd /home/pi/Jura-Python-BT/src/ && sudo ./backupMySQLdb.sh")
        os.system("sudo reboot")
        logging.info("Rebooting pi")

    if current_time % 5 == 0:
       
        child.sendline("char-write-req " +  CHARACTERISTICS["heartbeat"][1] + " " + keep_alive_code)
        data = child.readline()
        data += child.readline()
        if "Disconnected" in str(data):
            # run setup
            print("Disconnected here")
            logging.debug("Disconnected here")
            child.close()
            while True:
                try:
                    child = pexpect.spawn("gatttool -b " + DEVICE + " -I -t random")
                    # Connect to the device.
                    print("Connecting to ")
                    print(DEVICE)
                    child.sendline("connect")
                    #print(child.child_fd)
                    #try:
                    child.expect("Connection successful", timeout=5)
                    print("Connected!")
                    logging.info("Connected")
                    lock_status = "unlocked"
                    lock_status = lockUnlockMachine(locking_code, lock_status)
                    print("Machine locked!")
                    break
                except:
                    continue
        # child.sendline("char-read-hnd " + CHARACTERISTICS["product_progress"][1])
        # child.expect(": ")
        # data = child.readline()
        # data2 = [int(x, 16) for x in data.split()]
        # print("Encoded: ", data)
        # decoded = BtEncoder.encDecBytes(data2, KEY_DEC)
        # as_hex = ["%02x" % d for d in decoded]
        # print(as_hex)
        # data = [int(x, 16) for x in data.split()]
        # decoded = BtEncoder.encDecBytes(data, KEY_DEC)
        # print("Decoded: ", decoded)
        # # read machine status and get alerts:
        # child.sendline("char-read-hnd " + CHARACTERISTICS["machine_status"][1])
        # child.expect(": ")
        # data = child.readline()
        # print(b"Data: " + data)
        # data = [int(x, 16) for x in data.split()]
        # decoded = BtEncoder.encDecBytes(data, KEY_DEC)
        # print("\nDecoded data as HEX: " + " ".join(["%02x" % d for d in decoded]))
        # getAlerts(" ".join(["%02x" % d for d in decoded]))

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
            set_buylist(DB, "01", prod)
            print("Admin made a product that was not payed for")

    if uid_str != "0":
        print("last seen: ", lastSeen)
        product_made = False
        if admin_locked == 0:
            lcd.lcd_clear()

        if (uid_str == MASTERCARD1) or (uid_str == MASTERCARD2):
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
            time.sleep(1)
        
        elif admin_locked == 1:
            pass
        else:
            try:
                if lastSeen == "":
                    lastSeen = uid_str
                    value = get_value(DB, uid_str)
                    if value < 0:
                         # alert user in lcd that they need to charge balance
                        lcd.lcd_clear()
                        lcd.lcd_display_string("  Your balance is   ", 1)
                        lcd.lcd_display_string("       < 0!         ", 2)
                        lcd.lcd_display_string("  Please charge it  ", 3)
                        lcd.lcd_display_string("  Locking Machine   ", 4)
                        beep(0.5)
                        time.sleep(0.5)
                        beep(0.5)
                        time.sleep(0.5)
                        beep(0.5)
                        time.sleep(2)
                        lock_status = lockUnlockMachine(locking_code, lock_status)                        
                        print("User balance is < 0")
                        lastSeen = ""
                        client_to_pay = ""
                        disp_init = 1


                    else:
                        value_str = str("Balance: " + str('%.2f' % value) + " EUR")
                        lastName = get_name(DB, uid_str)
                        preName = get_vorname(DB, uid_str)                
                        welStr = str("Hello " + preName)
                        msgStr3 = str("Hold for 2s please  ")
                        msgStr4 = str("Chip below          ")

                        lcd.lcd_display_string(welStr, 1)
                        lcd.lcd_display_string(value_str, 2)
                        lcd.lcd_display_string(msgStr3, 3)
                        lcd.lcd_display_string(msgStr4, 4)
                        time.sleep(1.5)
                    
                elif lastSeen == uid_str and product_made == False:
                    beep(0.1)
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
                        if int(time.time() - intial_time_2) % 2 == 0:
                            child.sendline("char-write-req " + CHARACTERISTICS["heartbeat"][1] + " " + keep_alive_code)
                        try:
                            # read the data from product progress handle
                            child.sendline("char-read-hnd " + CHARACTERISTICS["product_progress"][1])
                            try: 
                                 child.expect(": ")
                            except:
                                 pass
                            data = child.readline()
                            data2 = [int(x, 16) for x in data.split()]
                            #print("Encoded: ", data)
                            data = [x for x in data.split()]
                            decoded = BtEncoder.encDecBytes(data2, KEY_DEC)
                            as_hex = ["%02x" % d for d in decoded]
                            if as_hex[1] not in ["3e", "00"] and time_total > 5 and started == 0:
                                #lock_status = lockUnlockMachine(locking_code, lock_status)
                                beep(0.5)
                                print("PRODUCT MADE")
                                client_to_pay = uid_str
                                lcd.lcd_clear()
                                preName = get_vorname(DB, uid_str) 
                                print("as_hex[2]: ", as_hex[2])
                                product_made = PRODUCTS[str(int(as_hex[2], 16))]
                                price_product = PRICECOFFEE[product_made]
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
                                    value_new = value - PRICECOFFEE[product_made]
                                if value_new > 0 and chosen == 1:
                                    print("PAYING")
                                    # beep(0.05)
                                    # time.sleep(0.1)
                                    # beep(0.05)
                                    set_value(DB, client_to_pay, value_new)
                                    payed_prod += 1
                                    total_prod += 1
                                    payment_to_date = 1
                                    preName = get_vorname(DB, client_to_pay) 
                                    #beep(1)
                                    set_buylist(DB, client_to_pay, product_made)
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
                                    set_value(DB, client_to_pay, value_new)
                                    payed_prod += 1
                                    total_prod += 1
                                    payment_to_date = 1
                                    #beep(1)
                                    set_buylist(DB, client_to_pay, product_made)
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
                                preName = get_vorname(DB, uid_str) 
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
                                # run setup
                                logging.debug("Disconnected")
                                child.close()
                                while True:
                                    try:
                                        child = pexpect.spawn("gatttool -b " + DEVICE + " -I -t random")
                                        # Connect to the device.
                                        print("Connecting to ")
                                        print(DEVICE)
                                        child.sendline("connect")
                                        child.expect("Connection successful", timeout=5)
                                        print("Connected!")
                                        logging.info("Connected")
                                        lock_status = "unlocked"
                                        lock_status = lockUnlockMachine(locking_code, lock_status)
                                        print("Machine locked!")
                                        break
                                    except:
                                        continue
                            except:
                                pass
                            continue
            except Exception as e:
                print("The error raised is: ", e)
                logging.error("The error raised is: " + str(e))
                try:
                    logging.debug("Disconnected")
                    child.close()
                    while True:
                        try:
                            child = pexpect.spawn("gatttool -b " + DEVICE + " -I -t random")
                            # Connect to the device.
                            print("Connecting to ")
                            print(DEVICE)
                            child.sendline("connect")
                            #print(child.child_fd)
                            #try:
                            child.expect("Connection successful", timeout=5)
                            print("Connected!")
                            logging.info("Connected")
                            lock_status = "unlocked"
                            lock_status = lockUnlockMachine(locking_code, lock_status)
                            print("Machine locked!")
                            break
                        except:
                            continue
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
            time.sleep(4)
            disp_init = 1
            client_to_pay = ""
            lastSeen = ""
            lock_status = lockUnlockMachine(locking_code, lock_status)
        time.sleep(0.1)                
