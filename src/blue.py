#!/usr/bin/env python3

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

characteristics = json.load(open("/home/pi/Jura-Python-BT/data/uuids_handles.json"))["characteristics"]
ALERTS = json.load(open("/home/pi/Jura-Python-BT/data/alerts.json"))["alerts"]
PRODUCTS = json.load(open("/home/pi/Jura-Python-BT/data/products.json"))["products"]
in_machine_products = json.load(open("/home/pi/Jura-Python-BT/data/in_machine_products.json"))["in_machine_products"]

print(PRODUCTS)
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
	# setupBuzzer(BuzzerPin)
	# GPIO.output(BuzzerPin, GPIO.HIGH)
	# time.sleep(duration)
	# GPIO.output(BuzzerPin, GPIO.LOW)
    print("beep off")

beep(0.5)

load_dotenv()

BtEncoder = BtEncoder()
JuraEncoder = JuraEncoder()

# BlackBetty2 mac address read from .env file
DEVICE = os.getenv("DEVICE")
print(DEVICE)

# get mastercard numbers from the .env file
mastercard1 = os.getenv("MASTER_CARD_1")
mastercard2 = os.getenv("MASTER_CARD_2")

# Open database connection
db = db_connect()

# Initialize LCD
lcd = lcddriver.lcd()
lcd.lcd_clear()  
lcd.lcd_display_string("  Starting Program  ", 1)
lcd.lcd_display_string("     Connecting     ", 2)
lcd.lcd_display_string("     Please wait!   ", 3)
lcd.lcd_display_string("  -----> :) <-----  ", 4)

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
    priceCoffee[key] = get_price(db, key)

print(priceCoffee)

# define function that locks or unlocks the machine
def lockUnlockMachine(code, lock_status, unlock_code = "77e1"):
    child.sendline("char-write-req " + characteristics["barista_mode"][1] + " " + code)
    #print(child.readline())
    #print(child.readline())
    if code == unlock_code:
        lock_status = "unlocked"
    else:
        lock_status = "locked"
    return lock_status

def readlineCR(port):
	rv = ""
	while True:
		ch = port.read()
		rv += ch
		if ch == '\r' or ch == '':
			return rv
                
#global RFIDREADER           
RFIDREADER = MFRC522.MFRC522()

# define function that scans for RFID card
def scanCard():
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
            print("Alert in bit " + str(i) + " with the alert " + ALERTS[str(i)])

# run the setup function 
child, keep_alive_code, locking_code, unlock_code, KEY_DEC, all_statistics, initial_time, CURRENT_STATISTICS = setup(DEVICE, characteristics)
print(getUID_stats(db))
if int(getUID_stats(db)) < CURRENT_STATISTICS[0]:
    # change the UID in the database Benutzerverwaltung to CURRENT_STATISTICS[0] where id = 1000
    print("updating the value in the table")
    c = db.cursor()
    c.execute("UPDATE Benutzerverwaltung SET UID = " + str(CURRENT_STATISTICS[0]) + " WHERE id = 1000;")	
    db.commit()
    c.close()

# function that runs if ctrl+c is pressed
def end_read(signal,frame):
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
	if int(getUID_stats(db)) < CURRENT_STATISTICS[0]:
		# change the UID in the database Benutzerverwaltung to CURRENT_STATISTICS[0] where id = 1000
		print("updating the value in the table from", getUID_stats(db), "to", CURRENT_STATISTICS[0])
		c = db.cursor()
		c.execute("UPDATE Benutzerverwaltung SET UID = " + str(CURRENT_STATISTICS[0]) + " WHERE id = 1000;")	
		db.commit()
		c.close()
	db.close()
	_ = lockUnlockMachine(unlock_code, "locked")
	exit(0)

# function that reads the statistics from the machine
def read_statistics():
    try:
        product_made = False
        # write the all statistics command to statistics_command_handle
        child.sendline("char-write-cmd " + characteristics["statistics_command"][1] + " " + all_statistics)
        #print("All statistics sent!")
        time.sleep(1.5)
        # read the data from product progress handle
        # read the statistics data from statistics_data_handle
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
        if int(getUID_stats(db)) < CURRENT_STATISTICS[0]:
            # change the UID in the database Benutzerverwaltung to CURRENT_STATISTICS[0] where id = 1000
            print("updating the value in the table from", getUID_stats(db), "to", CURRENT_STATISTICS[0])
            c = db.cursor()
            c.execute("UPDATE Benutzerverwaltung SET UID = " + str(CURRENT_STATISTICS[0]) + " WHERE id = 1000;")	
            db.commit()
            c.close()
        return product_made     
    except Exception as e:
         print("Error reading statistics!")
         logging.error("Error reading statistics " + str(e))
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

time.sleep(1)
while continue_reading:
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
        if int(getUID_stats(db)) < CURRENT_STATISTICS[0]:
            # change the UID in the database Benutzerverwaltung to CURRENT_STATISTICS[0] where id = 1000
            print("updating the value in the table")
            c = db.cursor()
            c.execute("UPDATE Benutzerverwaltung SET UID = " + str(CURRENT_STATISTICS[0]) + " WHERE id = 1000;")
            db.commit()
            c.close()
        print("Rebooting pi")
        lcd.lcd_clear()
        os.system("cd /home/pi/Jura-Python-BT/src/ && sudo ./backupMySQLdb.sh")
        os.system("sudo reboot")
        logging.info("Rebooting pi")

    if current_time % 5 == 0:
       
        child.sendline("char-write-req " +  characteristics["heartbeat"][1] + " " + keep_alive_code)
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
        # child.sendline("char-read-hnd " + characteristics["product_progress"][1])
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
        # child.sendline("char-read-hnd " + characteristics["machine_status"][1])
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
            set_buylist(db, "01", prod)
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
            time.sleep(1)
        
        elif admin_locked == 1:
            pass
        else:
            try:
                if lastSeen == "":
                    lastSeen = uid_str
                    value = get_value(db, uid_str)
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
                        lastName = get_name(db, uid_str)
                        preName = get_vorname(db, uid_str)                
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
                            child.sendline("char-write-req " + characteristics["heartbeat"][1] + " " + keep_alive_code)
                        try:
                            # read the data from product progress handle
                            child.sendline("char-read-hnd " + characteristics["product_progress"][1])
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
                                preName = get_vorname(db, uid_str) 
                                print("as_hex[2]: ", as_hex[2])
                                product_made = in_machine_products[str(int(as_hex[2], 16))]
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
                                    set_value(db, client_to_pay, value_new)
                                    payed_prod += 1
                                    total_prod += 1
                                    payment_to_date = 1
                                    preName = get_vorname(db, client_to_pay) 
                                    #beep(1)
                                    set_buylist(db, client_to_pay, product_made)
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
                                    set_value(db, client_to_pay, value_new)
                                    payed_prod += 1
                                    total_prod += 1
                                    payment_to_date = 1
                                    #beep(1)
                                    set_buylist(db, client_to_pay, product_made)
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
                                preName = get_vorname(db, uid_str) 
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
