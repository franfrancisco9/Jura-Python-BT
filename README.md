# Documentation - Jura Coffee Machine Bluetooth Conection

Disclaimer: This is repo is in active development with a focus on getting a working project so things may change or not work as intended. If you have any questions or suggestions please open an issue. When the project is finished there will be a more formal bluetooth protocol documentation.

This document serves as documentation for the bluetooth conection between the Jura Coffee Machine and a Raspberry Pi3, with the aim to explain all the steps to follow to make the connection between the two devices, as well as present possible problems and solutions.

The encoding and decoding are come from the [Jura Bluetooth Protocol](https://github.com/Jutta-Proto/protocol-cpp) project. A special shoutout to @COM8 for the help.

The table of contents is as follows:
- [Documentation - Jura Coffee Machine Bluetooth Conection](#documentation---jura-coffee-machine-bluetooth-conection)
  - [Project Flow](#project-flow)
  - [SSH connection to the Raspberry Pi3](#ssh-connection-to-the-raspberry-pi3)
  - [Bluetooth Conections](#bluetooth-conections)
    - [Obtaining the MAC Address](#obtaining-the-mac-address)
    - [Obatining the Manufacturer Key and Data](#obatining-the-manufacturer-key-and-data)
    - [Characteristics and Services](#characteristics-and-services)
  - [Main Script](#main-script)
  - [Common Errors and Solutions](#common-errors-and-solutions)
  - [Usefull Links](#usefull-links)

## Project Flow

The current project shows a possible implementation of the bluetooth connection between the Pi and the Jura coffee machine using a rfid reader, a lcd and a buzzer as well as a database to store the purchases, purchases and users. This is later presentend in a web interface using phpmyadmin.

Add a line to your ```/etc/rc.local``` file to start the script on boot:

```bash
sudo python3 /home/pi/Jura-Python-BT/src/blue.py >> /home/pi/Jura-Python-BT/src/templog.txt 2>&1 &
```

If you want to have logs in case of possible errors use the second part of the above code.

If your jura coffee machine is working and you have the correct setup using a rfid reader, a lcd and a buzzer you should be able to use this project out of the box.

The flow of the project is as follows:

1. The script is started on boot.
2. A message appears on the LCD letting the user know they must present their tag to the reader and the machine is locked.
3. The user presents the tag to the reader and the machine is unlocked.
4. The user can now select a product.
5. The product is detected and the purches is registered in the database.
6. The products ends and the program detects it and locks the machine again while also charging the user.
7. Repeat from step 2.

The code can be easily adjusted to not use the database and functions only with a lock unlock function using the rfid reader.

The statistics part of the code is to control how many products are being paid versus how many were actually made since a user could just unplug the Pi and not pay for the product.

## SSH connection to the Raspberry Pi3
To connect to the Raspberry Pi3 via SSH, the following command must be used:
```bash
ssh pi@IP_ADDRESS
```
Where IP_ADDRESS is the IP address of the Raspberry Pi3. 

The first time you connect you have to accept the fingerprint. Then you must enter the password. After that you inside the Raspberry Pi3.

## Bluetooth Conections
The Coffee Machine used is a `Jura Giga x8c` which is equipped with a bluetooth dongle that can be found by the name `TT214H BlueFrog` which is usually used to connect with the Jura app.

Raspberry Pi3 has a built-in bluetooth module, which can be used to connect to the coffee machine. 

Below are the steps to follow to make the connection between the two devices.

### Obtaining the MAC Address

The first step is to obtain the MAC address of the coffee machine. This can be done by using the `hcitool` command, which is a tool that allows to scan for bluetooth devices.

Make sure that the bluetooth module is turned on by using the command `sudo hciconfig hci0 up`. 

Then, use the command `sudo hcitool lescan` to scan for bluetooth devices. The output should be similar to the following:

```bash
pi@raspberrypi:~ $ sudo hcitool lescan
LE Scan ...
00:1A:7D:DA:71:13 (unknown)
00:1A:7D:DA:71:14 TT214H BlueFrog
```

The MAC address of the coffee machine is the one that is shown in the last line of the output. In this case, the MAC address is `00:1A:7D:DA:71:14`.

To pair and connect with the device we can use bluetoothctl command.

```bash
pi@raspberrypi:~ $ bluetoothctl
[NEW] Controller 00:1A:7D:DA:71:13 raspberrypi [default]
[NEW] Device 00:1A:7D:DA:71:14 TT214H BlueFrog
[bluetooth]# pair 00:1A:7D:DA:71:14
Attempting to pair with 00:1A:7D:DA:71:14
[CHG] Device 00:1A:7D:DA:71:14 Connected: yes
[CHG] Device 00:1A:7D:DA:71:14 ServicesResolved: yes
[CHG] Device 00:1A:7D:DA:71:14 Paired: yes
Pairing successful
[bluetooth]# connect 00:1A:7D:DA:71:14
Attempting to connect to 00:1A:7D:DA:71:14
[CHG] Device 00:1A:7D:DA:71:14 Connected: yes
Connection successful
[bluetooth]# trust 00:1A:7D:DA:71:14
[CHG] Device 00:1A:7D:DA:71:14 Trusted: yes
Changing 00:1A:7D:DA:71:14 trust succeeded
```

It is important to keep in mind that the coffee machine will disconnect every few seconds and will need to be connected again. So it is normal you see the following message:

```bash
[CHG] Device 00:1A:7D:DA:71:14 Connected: no
```

If you want to keep a connection with the coffee machine, you can use the following command:

```bash
pi@raspberrypi:~ $ for i in {1..100}; do bluetoothctl connect 00:1A:7D:DA:71:14; sleep 5; done
```

This command will try to connect to the coffee machine every 5 seconds, for 100 times. You can change the number of times you want to try to connect to the coffee machine by changing the number in the first line of the command. This allows to do some tests without having to connect to the coffee machine every time. Further down, we will see how to make a script that will allow us to connect to the coffee machine automatically (a heartbeat script).

### Obatining the Manufacturer Key and Data

The next step is to obtain the Manufacturer Key and Data. This can be done by using the `info` command inside the `bluetoothctl` menu.

```bash
[bluetooth]# info 00:1A:7D:DA:71:14
```

The output should be similar to the following:

```bash
   Name: TT214H BlueFrog
        Alias: TT214H BlueFrog
        Paired: yes
        Trusted: yes
        Blocked: no
        Connected: yes
        LegacyPairing: no
        UUID: Vendor specific           (00000000-0000-aaaa-0000-000aaaaaa000)
        UUID: Generic Access Profile    (00000000-0000-aaaa-0000-000aaaaaa000)
        UUID: Generic Attribute Profile (00000000-0000-aaaa-0000-000aaaaaa000)
        UUID: Vendor specific           (00000000-0000-aaaa-0000-000aaaaaa000)
        UUID: Vendor specific           (00000000-0000-aaaa-0000-000aaaaaa000)
        ManufacturerData Key: 0x0000
        ManufacturerData Value:
  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
  00 00 00 00 00 00 00 00 00 00 00                 ...........
```

The Manufacturer Key and Data are the ones that are shown in the last two lines of the output. In this case, the Manufacturer Key is `0x0000` and the Manufacturer Data is `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` (which is made up in this case).


### Characteristics and Services
Inside the bluetoothctl menu, we can use the `menu gatt` command to access the GATT menu. This menu allows us to see the characteristics and services of the coffee machine.

```bash
[bluetooth]# menu gatt
```

Inside this menu we can use the `list-attributes` command to see the characteristics and services of the coffee machine. Furthermore we can use the `select-attribute` command to select a specific characteristic or service. From there we can use the `read` and `write` commands to read and write to the characteristic or service.


I used the command read for all the attributes found with the command list-attributes. The results can be found in the file `services_and_characteristics.txt`. The file contains the UUID of the characteristic or service, the name of the characteristic or service, the value of the characteristic or service and the type of the characteristic or service. 



In case you do not see a bluetooth module in the bluetoothctl menu, you can install the necessary packages by using the following commands:

```bash
sudo apt-get install bluetooth bluez libbluetooth-dev libudev-dev
```

## Main Script

To run the main script, go into the `src` folder and run the following command:

```bash
sudo python3 blue.py
```

If you open a seperate terminal and run the command `bluetoothctl` you should see the following:

```bash
[TT214H BlueFrog]# 
```

Meaning that the script is running and the coffee machine is connected.

The script sends a heartbeat every 15 seconds. 

The script as it stands reads the machine status every second and converts it to the respective alerts that should appear on the terminal.

Furthermore if you send a message to the `start_product` characteristic, you can make a coffee. For more details check the repository mentioned in the beginning. 

## Common Errors and Solutions

## Usefull Links

* [Forum Domoticz](https://www.domoticz.com/forum/viewtopic.php?t=25128)
* [Hardware Pi](https://github.com/Jutta-Proto/hardware-pi)
* [ESPHome Jura Component](https://github.com/ryanalden/esphome-jura-component/issues/7)
* [ESP32 Jura](https://github.com/COM8/esp32-jura)
* [ESPHome Jura Component](https://github.com/ryanalden/esphome-jura-component)
* [Protocol BT CPP](https://github.com/Jutta-Proto/protocol-bt-cpp)

