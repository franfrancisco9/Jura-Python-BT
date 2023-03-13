import os
import time
from dotenv import load_dotenv
import pymysql  
pymysql.install_as_MySQLdb()
import MySQLdb as mdb
import logging

# create logger in blue.log in current directory
logging.basicConfig(
    filename='blue.log',
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

load_dotenv()

def db_connect():
    # Open database connection
    while True:
        try:
            db = mdb.connect(host = "127.0.0.1", user = "root", passwd = os.getenv("PASSWD"), db = "AnnelieseDB")
            return db 
        except:
            logging.info("Database connection failed. Trying again in 5 seconds...")
            time.sleep(5)
            continue

# Function to go to Benutzerverwaltung table and retrieve UID from id = 1000
def getUID_stats(db):
    value = str()
    c = db.cursor()
    db.commit()
    c.execute("SELECT SQL_NO_CACHE * FROM Benutzerverwaltung WHERE id = 1000 ")
    value = c.fetchone()[1]
    c.close
    return value  

# Function to get full name of given UID
def get_name(db, UID):
	c = db.cursor()
	db.commit()
	c.execute("SELECT SQL_NO_CACHE * FROM Benutzerverwaltung WHERE UID = " + UID + " ")
	for row in c.fetchall():
		name = row[2]
	c.close
	return name

# Function to get price of selected product
def get_price(db, product):
	price = float()
	c = db.cursor()
	db.commit()
	c.execute("SELECT SQL_NO_CACHE * FROM Produktliste WHERE Produkt = '" + product + "' ")
	for row in c.fetchall():
		price = row[2]
	c.close
	return price

# Function to get full name of given UID
def get_vorname(db, UID):
	c = db.cursor()
	db.commit()
	c.execute("SELECT SQL_NO_CACHE * FROM Benutzerverwaltung WHERE UID = " + UID + " ")
	for row in c.fetchall():
		vorname = row[3]
	c.close
	return vorname

# Function to get ID/chip number of given UID
def get_chip(db, UID):
	c = db.cursor()
	db.commit()
	c.execute("SELECT SQL_NO_CACHE * FROM Benutzerverwaltung WHERE UID = " + UID + " ")
	for row in c.fetchall():
		chip = row[0]
	c.close
	return chip

# Function to get value of given UID
def get_value(db, UID):
	value = float()
	c = db.cursor()
	db.commit()
	c.execute("SELECT SQL_NO_CACHE * FROM Benutzerverwaltung WHERE UID = " + UID + " ")
	for row in c.fetchall():
			value = row[4]
	c.close
	return value

# Function to set new value of given UID
def set_value(db, UID, value):
	c = db.cursor()
	c.execute("UPDATE Benutzerverwaltung SET Guthaben = " + str(value) + " WHERE UID = " + UID + " ")
	db.commit()
    # where ID = 1000
	current = int(getUID_stats(db))
	c.execute("UPDATE Benutzerverwaltung SET UID = " + str(current + 1) + " WHERE id = 1000;")	
	db.commit()
	c.close()
	
# Function to set insert new row into Kaufliste
def set_buylist(db, UID, product_name):
	chip = get_chip(db, UID)
	c = db.cursor()
	price = get_price(db, product_name)
	c.execute("INSERT INTO Kaufliste (ID, Chip, Produkt, Preis, Timestamp) VALUES (NULL, '" + str(chip) + "', '" + product_name + "', '" + str(price) + "', CURRENT_TIMESTAMP)")
	db.commit()
	c.close()