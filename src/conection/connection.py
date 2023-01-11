import MySQLdb as mdb
import RPi.GPIO as GPIO
import lcddriver
import MFRC522
import signal
import time
import serial
from bitarray import bitarray
import os
from dotenv import load_dotenv

load_dotenv()

# Define product commands from coffeemaker
products = "ABCDEFGHJ"
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

def setupBuzzer(pin):
	global BuzzerPin
	BuzzerPin = pin
	GPIO.setmode(GPIO.BOARD)	# Numbers GPIOs by physical location
	GPIO.setup(BuzzerPin, GPIO.OUT)
	GPIO.output(BuzzerPin, GPIO.HIGH)
	
def beep(duration):
	GPIO.output(BuzzerPin, GPIO.LOW)
	time.sleep(duration)
	GPIO.output(BuzzerPin, GPIO.HIGH)

# Define Mastercard to toggle lock and unlock
mastercard1 = os.getenv("mastercard1")
mastercard2 = os.getenv("mastercard2")

# Open database connection
db = mdb.connect(host = "localhost", user = "root", passwd = os.getenv("passwd"), db = "AnnelieseDB")

# Initialize LCD
lcd = lcddriver.lcd()
lcd.lcd_clear()

def sleepTimer(secs):
	startTime = time.time()
	while (time.time() - startTime) < secs:
		pass

# Capture SIGINT for cleanup when the script is aborted
def end_read(signal,frame):
	global continue_reading
	beep(3)
	print("Ctrl+C captured, ending read.")
	port.write("?iOFF")
	port.close()
	inkasso = 0
	lcd.lcd_display_string("  Programm beendet  ", 1)
	lcd.lcd_display_string("      ~~~~~~~~      ", 2)
	lcd.lcd_display_string("  Inkasso Modus aus ", 3)
	lcd.lcd_display_string("  -----> :( <-----  ", 4)
	time.sleep(1)
	lcd.lcd_clear()
	db.close()
	continue_reading = False
	GPIO.cleanup()

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
		
# # Hook the SIGINT
# signal.signal(signal.SIGINT, end_read)

# # Create an object of the class MFRC522
# MIFAREReader = MFRC522.MFRC522()

# # Init buzzer
# setupBuzzer(BUZZER)

# # Init Serial
# port = serial.Serial("/dev/serial0", baudrate = 9600, timeout = 1.0)
# print("Serial connection initialized")

# lcd.lcd_display_string("   Machine Locked   ", 1)
# lcd.lcd_display_string("      ~~~~~~~~      ", 2)
# lcd.lcd_display_string(" Put tag to unlock  ", 3)
# lcd.lcd_display_string("  -----> :) <-----  ", 4)
# time.sleep(1)
# beep(0.1)

# port.flushInput()

# buttonPress = False
# continue_reading = True

# # Welcome message
# print("Welcome to the K1ngLu1 Anneliese-Hack")
# print("Press Ctrl-C to stop.")

# lastSeen = ""
# counter = 0
# disp_init = 1

# # This loop keeps checking for chips. If one is near it will get the UID and authenticate
# while continue_reading:
# 	if disp_init == 1:
# 		lcd.lcd_clear()
# 		lcd.lcd_display_string("   Tag detected!    ", 1)
# 		lcd.lcd_display_string("   Choose Product   ", 2)
# 		lcd.lcd_display_string("     In machine     ", 3)
# 		lcd.lcd_display_string("         :)         ", 4)
# 		disp_init = 0
# 		time.sleep(0.5)

# 	uid_str = scanCard()

# 	if uid_str != "0":
		
# 		lcd.lcd_clear()
		
# 		if ((uid_str == mastercard1) or (uid_str == mastercard2)):
# 			if inkasso == 0:
# 				toCoffeemaker("?M3\r\n")
# 				inkasso = 1
# 				lcd.lcd_display_string("  Inkasso Modus an  ", 2)
# 				lcd.lcd_display_string("  -----> :) <-----  ", 3)
# 			elif inkasso == 1:
# 				toCoffeemaker("?M1\r\n")
# 				inkasso = 0
# 				lcd.lcd_display_string("  Inkasso Modus aus ", 2)
# 				lcd.lcd_display_string("  -----> :( <-----  ", 3)
				
# 			time.sleep(2)
# 			lcd.lcd_clear()

# 		else:
# 			try:
# 				if lastSeen == "":
# 					lastSeen = uid_str
# 					value = get_value(uid_str)
# 					value_str = str("Guthaben: " + str('%.2f' % value) + " EUR")
# 					lastName = get_name(uid_str)
# 					preName = get_vorname(uid_str)				
# 					welStr = str("Hallo " + preName)
# 					msgStr3 = str("Zum Buchen bitte 3 s")
# 					msgStr4 = str("Chip an Leser halten")

# 					lcd.lcd_display_string(welStr, 1)
# 					lcd.lcd_display_string(value_str, 2)
# 					lcd.lcd_display_string(msgStr3, 3)
# 					lcd.lcd_display_string(msgStr4, 4)
# 					time.sleep(2)
                    
# 				elif lastSeen == uid_str:
# 					lcd.lcd_clear()
# 					value = get_value(uid_str)
# 					value_new = (value - get_price(product="Coffee"))
					
# 					if value_new >= 0:
						
# 						beep(0.05)
# 						time.sleep(0.1)
# 						beep(0.05)
# 						set_value(uid_str, value_new)
# 						set_buylist(uid_str, str("General"), 0.5)
# 						msgStr1 = str(" Kaffee abgebucht!")
# 						msgStr2 = str("  Betty dankt :)  ")
# 						value_str = str("Guthaben: " + str('%.2f' % value_new) + " EUR")
# 						lcd.lcd_display_string(msgStr1, 1)
# 						lcd.lcd_display_string(msgStr2, 2)
# 						lcd.lcd_display_string(value_str, 4)
# 						sleepTimer(4)
# 						lcd.lcd_clear()
# 						lastSeen = ""
# 						counter = 0
# 						disp_init = 1
# 					else:
# 						lcd.lcd_clear()
# 						set_value(uid_str, value_new)
# 						set_buylist(uid_str, str("General"), 0.5)
# 						msgStr1 =   str(" Kaffee abgebucht!")
# 						msgStr2 =   str(" Schulden gemacht!")
# 						msgStr3 =   str("Guthaben aufladen!")
# 						#value_str = str("Schulden: " + str('%.2f' % (-1*value))) + " EUR")
# 						lcd.lcd_display_string(msgStr1, 1)
# 						lcd.lcd_display_string(msgStr2, 2)
# 						lcd.lcd_display_string(msgStr2, 3)
# 						lcd.lcd_display_string(value_str, 4)
# 						beep(0.05)
# 						time.sleep(0.1)
# 						beep(0.05)
# 						beep(0.5)
# 						time.sleep(4)
# 						lastSeen = ""
# 						counter = 0
# 						disp_init = 1
# 				else:
# 					lcd.lcd_clear()
# 					lastName1 = get_name(lastSeen)
# 					PreName1 = get_vorname(lastSeen)
# 					lastName2 = get_name(uid_str)
# 					PreName2 = get_vorname(uid_str)
# 					msgStr1 = str("Andere UID! Erwarte:")
# 					msgStr2 = str(preName1 + " " + lastName1)
# 					msgStr3 = str("Gerade gelesen: ")
# 					msgStr4 = str(preName2 + " " + lastName2)
# 					lcd.lcd_display_string(msgStr1, 1)
# 					lcd.lcd_display_string(msgStr2, 2)
# 					lcd.lcd_display_string(msgStr3, 3)
# 					lcd.lcd_display_string(msgStr4, 4)
# 					beep(0.5)
# 					time.sleep(3)
# 					lastSeen = ""
# 					counter = 0
# 					disp_init = 1
			
# 			except:
# 				#lcd.lcd_display_string("Unbekannte Karte", 2)
# 				#lcd.lcd_display_string("UID: " + uid_str, 3)
# 				print("Card read UID: " + uid_str)
# 				#beep(1)
# 				time.sleep(1)
# 				#lcd.lcd_clear()
	
# 	else:
# 		if lastSeen != "":
# 			counter = counter + 1
# 			print(counter)
# 		if counter >= 10:
# 			lcd.lcd_clear()
# 			lastSeen = ""
# 			counter = 0
# 			beep(0.2)
# 			time.sleep(0.1)
# 			beep(0.2)

# 			msgStr1 = str("Chip entfernt?")
# 			msgStr3 = str("Kaffe konnte nicht")
# 			msgStr4 = str("gebucht werden! :(")
# 			lcd.lcd_display_string(msgStr1, 1)
# 			lcd.lcd_display_string(msgStr3, 3)
# 			lcd.lcd_display_string(msgStr4, 4)
# 			sleepTimer(4)
# 			disp_init = 1
# 		sleepTimer(0.1)				
"""
	rcv = fromCoffeemaker()
	
	if len(rcv) > 0 and rcv[1][0] != 'o':
		print "Received String: " + rcv
		print "Length: " + str(len(rcv))
		beep(0.1)
		lcd.lcd_clear()
		
		if rcv[0][0] == '?' and rcv[1][0] == 'P' and rcv[2][0] == 'A':
			product = 255
			for k in range(0, len(products)):
				if rcv[3][0] == products[k][0]:
					product = k + 1
					break
			if product != 255:
				if product == 9:	# Produkte, die nicht vorne am Display angezeigt werden liefern ?PAJ, was Produkt 9 entspricht
					lcd.lcd_display_string("ERROR", 1)
					lcd.lcd_display_string("Bitte Produkt auf", 2)
					lcd.lcd_display_string("Display waehlen!!!", 3)
					lcd.lcd_display_string("Vielen Dank! ;-)", 4)
					beep(1)
					time.sleep(2)
					lcd.lcd_clear()
				else:
					product_name = get_product(product)
					price = get_price(product)

					lcd.lcd_display_string(product_name, 2)
					lcd.lcd_display_string(str('%.2f' % price) + " EUR", 3)
					buttonPress = True
					t_end = time.time() + 2.5
		else:
			lcd.lcd_display_string("Unbekanntes Produkt!", 2)
			lcd.lcd_display_string("CM: " + rcv, 3)
			time.sleep(2)
			lcd.lcd_clear()
			
	while buttonPress == True:
			
		uid_str = scanCard()	
			
		if uid_str != "0":
			beep(0.1)
			try:
				value = get_value(uid_str)
				value_str = str("Guthaben: " + str('%.2f' % value) + " EUR")
				name = get_name(uid_str)
				vorname = get_vorname(uid_str)
				print "Card read UID: " + uid_str
				print name + " " + vorname
				print value_str

			except:
				lcd.lcd_clear()
				lcd.lcd_display_string("Unbekannte Karte", 2)
				lcd.lcd_display_string("UID: " + uid_str, 3)
				beep(1)
				time.sleep(2)
				lcd.lcd_clear()
				buttonPress = False
				break
		
			value_new = value - price

			if value_new >= 0:
				toCoffeemaker("?ok\r\n")
				set_value(uid_str, value_new)
				set_buylist(uid_str, product_name, price)
				value_str = str("Guthaben: " + str('%.2f' % value_new) + " EUR")      
		
				print "Neuer " + value_str
				
				lcd.lcd_display_string("Vielen Dank", 1)
				lcd.lcd_display_string(product_name, 2)
				lcd.lcd_display_string("bezahlt!", 3)
				lcd.lcd_display_string(value_str, 4)
				
				if value <= 2:
					beep(0.05)
					time.sleep(0.05)
					beep(0.05)
				
				time.sleep(5)

			else:
				beep(1)
				print "Guthaben ist nicht mehr ausreichend!"
				print "Bitte aufladen."
				lcd.lcd_display_string("Guthaben: " + str(value) + " EUR", 2)
				lcd.lcd_display_string("Bitte aufladen!!", 3)
				time.sleep(2)
			
			buttonPress = False
	
		if time.time() > t_end:
			buttonPress = False
"""
