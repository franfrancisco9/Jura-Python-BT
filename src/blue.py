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
def setupBuzzer(pin):
	global BuzzerPin
	BuzzerPin = pin
	GPIO.setmode(GPIO.BOARD)	# Numbers GPIOs by physical location
	GPIO.setup(BuzzerPin, GPIO.OUT)
	GPIO.output(BuzzerPin, GPIO.LOW)
	
def beep(duration):
	GPIO.output(BuzzerPin, GPIO.HIGH)
	time.sleep(duration)
	GPIO.output(BuzzerPin, GPIO.LOW)

# Define pin for buzzer
BUZZER = 7
# Init buzzer
setupBuzzer(BUZZER)
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
    9:"Flat White",
    58:"Something"
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

def lockUnlockMachine(code, lock_status):
    child.sendline("char-write-req " + barista_mode_handle + " " + code)
    print(child.readline())
    print(child.readline())
    if lock_status == "locked":
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

# Function to get price of selected product
def get_price(product):
	price = priceCoffee[product]
	return price

# Function to set insert new row into Kaufliste
def set_buylist(UID, product_name, price):
	chip = get_chip(UID)
	c = db.cursor()
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

def scanCard():
	# Scan for cards    
	(status,TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)

    # If a card is found
	if status == MIFAREReader.MI_OK:
		print("Card detected")
    
    # Get the UID of the card
	(status,uid) = MIFAREReader.MFRC522_Anticoll()

    # If we have the UID, continue
	if status == MIFAREReader.MI_OK:
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


child, keep_alive_code, locking_code, unlock_code, KEY_DEC, all_statistics, initial_time, CURRENT_STATISTICS = setup(DEVICE, characteristics)
# Capture SIGINT for cleanup when the script is aborted
def end_read(signal,frame):
	global continue_reading
	beep(2)
	print("Ctrl+C captured, ending read.")
	inkasso = 0
	lcd.lcd_display_string("  Programm beendet  ", 1)
	lcd.lcd_display_string("      ~~~~~~~~      ", 2)
	lcd.lcd_display_string("     Unlocking      ", 3)
	lcd.lcd_display_string("  -----> :( <-----  ", 4)
	time.sleep(1)
	lcd.lcd_clear()
	db.close()
	continue_reading = False
	GPIO.cleanup()
	_ = lockUnlockMachine(unlock_code, "locked")
emergency_unlock = 1
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
while continue_reading:
    # if time elapsed is a multiple of 15 seconds then send keep alive code
    if int(time.time() - initial_time) % 5 == 0:
        # print time in seconds since it was connected
        #print("\nTime elapsed: " + str(int(time.time() - initial_time)))
        child.sendline("char-write-req " + heartbeat_handle + " " + keep_alive_code)
        #print("Keep alive sent!") 
        child.sendline("char-read-hnd " + product_progress_handle)
        child.expect(": ")
        data = child.readline()
        print(data)
        data = [int(x, 16) for x in data.split()]
        decoded = BtEncoder.encDecBytes(data, KEY_DEC)
        # join decoded data to a list for every three bytes example: [001200, 000000, 000098]
        decoded = ["".join(["%02x" % d for d in decoded[i:i+3]]) for i in range(0, len(decoded), 3)]
        
        # for every hex string in decoded list, convert to int
        decoded = [int(x, 16) for x in decoded] 
        print("Product progress data: " + str(decoded))
        # read machine status and get alerts:
        child.sendline("char-read-hnd " + machine_status_handle)
        child.expect(": ")
        data = child.readline()
        print(b"Data: " + data)
        data = [int(x, 16) for x in data.split()]
        decoded = BtEncoder.encDecBytes(data, KEY_DEC)
        print("\nDecoded data as HEX: " + " ".join(["%02x" % d for d in decoded]))
        getAlerts(" ".join(["%02x" % d for d in decoded]))


    if disp_init == 1:
        lcd.lcd_clear()
        lcd.lcd_display_string("  Put Tag and then  ", 1)
        lcd.lcd_display_string("   Choose Product   ", 2)
        lcd.lcd_display_string("     In machine     ", 3)
        lcd.lcd_display_string("         :)         ", 4)
        disp_init = 0
        time.sleep(0.5)

    if payment_to_date == 0:
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
        if decoded[0] != CURRENT_STATISTICS[0]:
            #lock_status = lockUnlockMachine(locking_code, lock_status)
            print("Overall products increased by 1")
            CURRENT_STATISTICS[0] = decoded[0]
            
        for i in range(1, len(decoded)):
            if decoded[i] != CURRENT_STATISTICS[i]:
                print("A " + PRODUCTS[i] + " was made!")
                product_made = PRODUCTS[i]
                chosen = 1
                print("Value changed: " + str(decoded[i]) + " -> " + str(CURRENT_STATISTICS[i]))
                CURRENT_STATISTICS[i] = decoded[i]
        if chosen == 1:    
            print("Setting value for uid: " + lastSeen)
            value_new = value - priceCoffee[product_made]
        if value_new >= 0 and chosen == 1:
            # beep(0.05)
            # time.sleep(0.1)
            # beep(0.05)
            set_value(uid_str, value_new)
            payment_to_date = 1
            #set_buylist(uid_str, str("General"), priceCoffee[product_made])
            # msgStr1 = str(" Kaffee abgebucht!")
            # msgStr2 = str("  Betty dankt :)  ")
            # value_str = str("Guthaben: " + str('%.2f' % value_new) + " EUR")
            # lcd.lcd_display_string(msgStr1, 1)
            # lcd.lcd_display_string(msgStr2, 2)
            # lcd.lcd_display_string(value_str, 4)
            # sleepTimer(4)
            # lcd.lcd_clear()
            lastSeen = ""
            counter = 0
            disp_init = 1
            product_made = False
        elif value_new < 0 and chosen == 1:
            lcd.lcd_clear()
            set_value(uid_str, value_new)
            payment_to_date = 1
            #set_buylist(uid_str, str("General"), 0.5)
            # msgStr1 =   str(" Kaffee abgebucht!")
            # msgStr2 =   str(" Schulden gemacht!")
            # msgStr3 =   str("Guthaben aufladen!")
            # #value_str = str("Schulden: " + str('%.2f' % (-1*value))) + " EUR")
            # lcd.lcd_display_string(msgStr1, 1)
            # lcd.lcd_display_string(msgStr2, 2)
            # lcd.lcd_display_string(msgStr2, 3)
            # lcd.lcd_display_string(value_str, 4)
            # beep(0.05)
            # time.sleep(0.1)
            # beep(0.05)
            # beep(0.05)
            # time.sleep(4)
            lastSeen = ""
            counter = 0
            disp_init = 1
            product_made = False
    uid_str = scanCard() 
    #print("UID: " + uid_str)
    # if int(time.time() - initial_time) in [20, 21, 22, 23]:
    #     uid_str = "204093081213"

    if uid_str != "0":
        
        product_made = False
        lcd.lcd_clear()

        if ((uid_str == mastercard1) or (uid_str == mastercard2)):
            if lock_status == "locked":
                lock_status = lockUnlockMachine(unlock_code, lock_status)
                print("Machine unlocked permanently!")
                lcd.lcd_display_string("    Admin Unlock    ", 2)
                lcd.lcd_display_string("  -----> :) <-----  ", 3)

            elif lock_status == "unlocked":
                lock_status = lockUnlockMachine(locking_code, lock_status)
                print("Machine locked!")
                lcd.lcd_display_string("    Admin Lock      ", 2)
                lcd.lcd_display_string("  -----> :( <-----  ", 3)
                disp_init = 1
            time.sleep(2)
            
        else:
            try:
                if lastSeen == "":
                    lastSeen = uid_str
                    value = get_value(uid_str)
                    value_str = str("Guthaben: " + str('%.2f' % value) + " EUR")
                    lastName = get_name(uid_str)
                    preName = get_vorname(uid_str)                
                    welStr = str("Hallo " + preName)
                    msgStr3 = str("Zum Buchen bitte 2 s")
                    msgStr4 = str("Chip an Leser halten")

                    lcd.lcd_display_string(welStr, 1)
                    lcd.lcd_display_string(value_str, 2)
                    lcd.lcd_display_string(msgStr3, 3)
                    lcd.lcd_display_string(msgStr4, 4)
                    time.sleep(1)
                    
                elif lastSeen == uid_str and product_made == False:
                    print("Opening coffe machine for choice")
                    lcd.lcd_clear()

                    lcd.lcd_display_string("    Wählen Sie      ", 1)
                    lcd.lcd_display_string("    ein Produkt     ", 2)
                    lcd.lcd_display_string("  in der Maschine   ", 3)
                    lcd.lcd_display_string("  -----> :) <-----  ", 4)
                    lock_status = lockUnlockMachine(unlock_code, lock_status)
                    initial_time = time.time()
                    chosen = 0
                    started = 0
                    # write the all statistics command to statistics_command_handle
                    child.sendline("char-write-req " + statistics_command_handle + " " + all_statistics)
                    #print("All statistics sent!")
                    time.sleep(1)
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
                    CURRENT_STATISTICS = decoded
                    while product_made == False:
                        print("Waiting for product to be made")
                        time_total = int(time.time() - initial_time)
                        if time_total > 10 and started == 0:
                            print("No product made in 10 seconds, locking machine")
                            lock_status = lockUnlockMachine(locking_code, lock_status)
                            lcd.lcd_display_string("  Kein Produkt      ", 1)
                            lcd.lcd_display_string("    ausgewählt      ", 2)
                            lcd.lcd_display_string("  Locking Machine   ", 3)
                            lcd.lcd_display_string("  -----> :( <-----  ", 4)
                            #lcd.lcd_clear()
                            disp_init = 1
                            chosen = 0
                            lock_status = lockUnlockMachine(locking_code, lock_status)
                            break
                        if int(time.time() - initial_time) % 5 == 0:
                            child.sendline("char-write-req " + heartbeat_handle + " " + keep_alive_code)
                        try:
                            # write the all statistics command to statistics_command_handle
                            child.sendline("char-write-req " + statistics_command_handle + " " + all_statistics)
                            #print("All statistics sent!")
                            #time.sleep(1.5)
                            # read the data from product progress handle
                            child.sendline("char-read-hnd " + product_progress_handle)
                            child.expect(": ")
                            data = child.readline()
                            data = [x for x in data.split()]
                            if data[1] != b"e1" and time_total > 5:
                                #lock_status = lockUnlockMachine(locking_code, lock_status)
                                beep(0.5)
                                print("PRODUCT MADE")
                                client_to_pay = uid_str
                                started = 1
                                lock_status = lockUnlockMachine(locking_code, lock_status)
                                payment_to_date = 0
                            else:
                                print("NO PRODUCT MADE")
                            #print("Product progress data: " + str(data))
                            # # read the statistics data from statistics_data_handle
                            # child.sendline("char-read-hnd " + statistics_data_handle)
                            # child.expect(": ")
                            # data = child.readline()
                            # #print(b"Statistics data: " + data)
                            # # decode the statistics data
                            # data = [int(x, 16) for x in data.split()]
                            # decoded = BtEncoder.encDecBytes(data, KEY_DEC)
                            # # join decoded data to a list for every three bytes example: [001200, 000000, 000098]
                            # decoded = ["".join(["%02x" % d for d in decoded[i:i+3]]) for i in range(0, len(decoded), 3)]
                            # # for every hex string in decoded list, convert to int
                            # decoded = [int(x, 16) for x in decoded]
                            # # change the values that are different from the previous ones when comparing with CURRENT_STATISTICS
                            # if decoded[0] != CURRENT_STATISTICS[0]:
                            #     #lock_status = lockUnlockMachine(locking_code, lock_status)
                            #     print("Overall products increased by 1")
                            #     CURRENT_STATISTICS[0] = decoded[0]
                                
                            # for i in range(1, len(decoded)):
                            #     if decoded[i] != CURRENT_STATISTICS[i]:
                            #         print("A " + PRODUCTS[i] + " was made!")
                            #         product_made = PRODUCTS[i]
                            #         chosen = 1
                            #         print("Value changed: " + str(decoded[i]) + " -> " + str(CURRENT_STATISTICS[i]))
                            #         CURRENT_STATISTICS[i] = decoded[i]
                        except Exception as e:
                           print("Error: " + str(e))
                           continue
                    # if chosen == 0:
                    #     product_made = False
                    #     continue
                    # elif chosen == 1:    
                    #     print("Setting value for uid: " + uid_str)
                    #     value_new = value - priceCoffee[product_made]
                    # if value_new >= 0 and chosen == 1:
                    #     beep(0.05)
                    #     time.sleep(0.1)
                    #     beep(0.05)
                    #     set_value(uid_str, value_new)
                    #     #set_buylist(uid_str, str("General"), priceCoffee[product_made])
                    #     msgStr1 = str(" Kaffee abgebucht!")
                    #     msgStr2 = str("  Betty dankt :)  ")
                    #     value_str = str("Guthaben: " + str('%.2f' % value_new) + " EUR")
                    #     lcd.lcd_display_string(msgStr1, 1)
                    #     lcd.lcd_display_string(msgStr2, 2)
                    #     lcd.lcd_display_string(value_str, 4)
                    #     sleepTimer(4)
                    #     lcd.lcd_clear()
                    #     lastSeen = ""
                    #     counter = 0
                    #     disp_init = 1
                    #     product_made = False
                    # elif value_new < 0 and chosen == 1:
                    #     lcd.lcd_clear()
                    #     #set_value(uid_str, value_new)
                    #     #set_buylist(uid_str, str("General"), 0.5)
                    #     msgStr1 =   str(" Kaffee abgebucht!")
                    #     msgStr2 =   str(" Schulden gemacht!")
                    #     msgStr3 =   str("Guthaben aufladen!")
                    #     #value_str = str("Schulden: " + str('%.2f' % (-1*value))) + " EUR")
                    #     lcd.lcd_display_string(msgStr1, 1)
                    #     lcd.lcd_display_string(msgStr2, 2)
                    #     lcd.lcd_display_string(msgStr2, 3)
                    #     lcd.lcd_display_string(value_str, 4)
                    #     beep(0.05)
                    #     time.sleep(0.1)
                    #     beep(0.05)
                    #     beep(0.05)
                    #     time.sleep(4)
                    #     lastSeen = ""
                    #     counter = 0
                    #     disp_init = 1
                    #     product_made = False
                # else:
                #     lcd.lcd_clear()
                #     lastName1 = get_name(lastSeen)
                #     PreName1 = get_vorname(lastSeen)
                #     lastName2 = get_name(uid_str)
                #     PreName2 = get_vorname(uid_str)
                #     msgStr1 = str("Andere UID! Erwarte:")
                #     msgStr2 = str(preName1 + " " + lastName1)
                #     msgStr3 = str("Gerade gelesen: ")
                #     msgStr4 = str(preName2 + " " + lastName2)
                #     lcd.lcd_display_string(msgStr1, 1)
                #     lcd.lcd_display_string(msgStr2, 2)
                #     lcd.lcd_display_string(msgStr3, 3)
                #     lcd.lcd_display_string(msgStr4, 4)
                #     beep(0.5)
                #     time.sleep(3)
                #     lastSeen = ""
                #     counter = 0
                #     disp_init = 1
            
            except Exception as e:
                print("The error raised is: ", e)
    
    # else:
    #     if lastSeen != "":
    #         counter = counter + 1
    #         print(counter)
    #     if counter >= 10:
    #         lcd.lcd_clear()
    #         lastSeen = ""
    #         counter = 0
    #         beep(0.2)
    #         time.sleep(0.1)
    #         beep(0.2)

    #         msgStr1 = str("Chip entfernt?")
    #         msgStr3 = str("Kaffe konnte nicht")
    #         msgStr4 = str("gebucht werden! :(")
    #         lcd.lcd_display_string(msgStr1, 1)
    #         lcd.lcd_display_string(msgStr3, 3)
    #         lcd.lcd_display_string(msgStr4, 4)
    #         sleepTimer(4)
    #         disp_init = 1
        sleepTimer(0.1)                

    
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

