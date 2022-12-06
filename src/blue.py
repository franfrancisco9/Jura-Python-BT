import pexpect
import time
from bt_encoder import BtEncoder
from jura_encoder import JuraEncoder

BtEncoder = BtEncoder()
JuraEncoder = JuraEncoder()

# BlackBetty2 mac address
DEVICE = "ED:95:43:60:13:92"

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

# code_coffee = "2A 03 00 04 14 00 00 01 00 01 00 00 00 00 00 2A"
# code_coffee = [int(x, 16) for x in code_coffee.split()]
# code_coffee = BtEncoder.encDecBytes(code_coffee, "00")
# code_coffee = "".join(["%02x" % d for d in code_coffee])
# print(code_coffee)

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

statistics_data_uuid = "5A401534-ab2e-2548-c435-08c300000710"
statistics_data_handle = "0x0029"

uart_rx_uuid = "5a401624-ab2e-2548-c435-08c300000710"
uart_rx_hnd = "0x0036"

uart_tx_uuid = "5a401625-ab2e-2548-c435-08c300000710"
uart_tx_hnd = "0x0039"

#keep_alive_code = "0e f7 2a"


# make dictionary with name: [uuid, handle]
characteristics = {
    "machine_status": [machine_status, machine_status_handle],
    "barista_mode": [barista_mode, barista_mode_handle],
    "product_progress": [product_progress, product_progress_handle],
    "heartbeat": [heartbeat_uuid, heartbeat_handle],
    "heartbeat_read": [heartbeat_read_uuid, heartbeat_read_handle],
    "start_product": [start_product, start_product_handle],
    "statistics_data": [statistics_data_uuid, statistics_data_handle],
    "uart_tx": [uart_tx_uuid, uart_tx_hnd],
    "uart_rx": [uart_rx_uuid, uart_rx_hnd]
}

# send command gatttool -b ED:95:43:60:13:92 -I -t random to system with no output using pexpect
# then send command connect to gatttool 
# then send command char-write-cmd 0x0011 0e f7 2a to gatttool

# gatttool -b ED:95:43:60:13:92 -I -t random
# connect
# char-write-req 0x0011 0e f7 2a

while True:
    print("Run gatttool...")
    child = pexpect.spawn("gatttool -b " + DEVICE + " -I -t random")
    # Connect to the device.
    print("Connecting to ")
    print(DEVICE)
    child.sendline("connect")
    try:
        child.expect("Connection successful", timeout=5)
        print("Connected!")
        # print the time the connection was made
        initial_time = time.time()
        print("Initial time: " + str(initial_time))
        time.sleep(5)
        # get current key
        child.sendline("char-read-hnd " + characteristics["machine_status"][1])
        child.expect(": ", timeout=5)
        data = child.readline()
        #print(data)
        KEY_DEC = BtEncoder.bruteforce_key(data)
        print("Key: ", KEY_DEC)
        data = [int(x, 16) for x in data.split()]
        decoded = BtEncoder.encDecBytes(data, KEY_DEC)
        print("\nDecoded data as HEX: " + " ".join(["%02x" % d for d in decoded]))
        keep_alive_code = KEY_DEC + " 7F 80"
        # encode keep alive code
        keep_alive_code = BtEncoder.encDecBytes([int(x, 16) for x in keep_alive_code.split()], KEY_DEC)
        keep_alive_code = "".join(["%02x" % d for d in keep_alive_code])
        break
    except:
        print("Failed to connect to device. Retrying...")
        continue
while True:
    time.sleep(1)
    child.sendline("char-read-hnd " + heartbeat_handle)
    child.expect(": ")
    #print(child.readline())
    # if time elapsed is a multiple of 15 seconds then send keep alive code
    if int(time.time() - initial_time) % 10 == 0:
        # print time in seconds since it was connected
        print("\nTime elapsed: " + str(int(time.time() - initial_time)))
        child.sendline("char-write-req " + heartbeat_handle + " " + keep_alive_code)
        print("Keep alive sent!")    
    # if int(time.time() - initial_time) == 20:
    #     child.sendline("char-write-req " + heartbeat_handle + " 771b35")
    #     print("Machine Restarted!")
    # Every 5 seconds read all characteristics and decode them to hex using BtEncoder.encDecBytes
    if int(time.time() - initial_time) % 5 == 0:
        for key in characteristics:
            # get only machine_status, heartbeat_read and product_progress
            if  key == "machine_status" or key == "uart_rx": # or key == "machine_status":
                print("\nCurrently reading: " + key)
                child.sendline("char-read-hnd " + characteristics[key][1])
                child.expect(": ")
                data = child.readline()
                print(b"Data: " + data)
                try: 
                    data = [int(x, 16) for x in data.split()]
                    decoded = BtEncoder.encDecBytes(data, KEY_DEC)
                    #print("Decoded data as INT: " + str(decoded))
                    
                    # if key is machine_status, decode it to alerts
                    if key == "machine_status":
                        print("\nDecoded data as HEX: " + " ".join(["%02x" % d for d in decoded]))
                        getAlerts(" ".join(["%02x" % d for d in decoded]))
                    elif key == "uart_tx":
                        #print(data)
                        #print("UART Tx not decoded: " + " ".join(["%02x" % d for d in decoded[1:]]))
                        print("UART Tx: \n" + "".join([chr(d) for d in decoded[1:]]))
                        print("\n As hex:\n" + " ".join(["%02x" % d for d in decoded]))
                    elif key == "uart_rx" and data[0] != 0:
                        #continue
                        #print(data)
                        print("UART Rx: \n" + "".join([chr(d) for d in decoded[1:]]))
                        print("\n As hex:\n" + " ".join(["%02x" % d for d in decoded]))

                except:
                    print("Error decoding data due to " + str(data))

    #at 35 seconds send the following command: char-write-req 0x000e 77 e9 3d d5 53 81 d3 db a3 2b fa 98 a4 a3 fa f9
    # if int(time.time() - initial_time) in [15, 16]:                     #2A 03 00 04 14 00 00 01 00 01 00 00 00 00 00 2A    
    #     child.sendline("char-write-req " + start_product_handle + " " + "77e93dd55381d3dba32bfa98a4a3faf9")
    #     print("Start product sent!")
    if int(time.time() - initial_time) in [30, 31, 32]:# and False:     
        command = b"TY:\r\n" # FN:89 to enter and FN:90 to exit
        command = [KEY_DEC + " " + JuraEncoder.tojura(chr(c).encode(), 1) for c in command]
        command = [BtEncoder.encDecBytes([int(x, 16) for x in i.split()], KEY_DEC) for i in command]
        command = ["".join(["%02x" % d for d in i]) for i in command]
        print("Command: " + str(command))
        # for each command send wait 8 milleniums and send the next command
        # for c in command:
        child.sendline("char-write-req " + uart_tx_hnd + " " + command[0])
        print(child.readline())
        print(child.readline())
        #time.sleep(1.5)
        print("TY Test Sent")

        # # get current key
        # child.sendline("char-read-hnd " + characteristics["machine_status"][1])
        # child.expect(": ", timeout=5)
        # data = child.readline()
        # print(child.readline())
        # KEY_DEC = BtEncoder.bruteforce_key(data)
        # print("Key: ", KEY_DEC)
        # keep_alive_code = KEY_DEC + " 7F 80"
        # # encode keep alive code
        # keep_alive_code = BtEncoder.encDecBytes([int(x, 16) for x in keep_alive_code.split()], KEY_DEC)
        # keep_alive_code = "".join(["%02x" % d for d in keep_alive_code])
        # data = [int(x, 16) for x in data.split()]
        # decoded = BtEncoder.encDecBytes(data, KEY_DEC)
        # print("\nDecoded data as HEX: " + " ".join(["%02x" % d for d in decoded]))
        
