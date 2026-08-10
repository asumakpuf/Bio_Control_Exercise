#Instructions for the installation of Fable 2.0

1.- Go to requirements.txt and install all the python (version >= 3.4) modules using pip.
2.- For Linux users you need to follow these steps in order to be able to connect to the dongle:
		Step0: Open a new terminal
		Step1: 
			cd /etc/udev/rules.d
		Step2: Create a file
			sudo nano my-usb.rules
		Step3: When you have the file open you should include the following lines:
			---------------------------------------------------------------------------------------------------------
			# Copy this file to /etc/udev/rules.d/
			KERNEL=="ttyACM0", RUN+="/bin/setserial /dev/ttyACM0 low_latency"
			KERNEL=="ttyACM1", RUN+="/bin/setserial /dev/ttyACM1 low_latency"


			ACTION!="add|change", GOTO="openocd_rules_end"
			SUBSYSTEM!="usb|tty|hidraw", GOTO="openocd_rules_end"
			# Please keep this list sorted by VID:PID

			#fable Atmel Corp.
			ATTRS{idVendor}=="03eb", ATTRS{idProduct}=="fabe", MODE="0666", GROUP="dialout"

			LABEL="openocd_rules_end"
			---------------------------------------------------------------------------------------------------------
			
			Notice that you can get the information "idVendor" and "idProduct" by:
			Open a terminal and: 
				lsusb
			The output should look like this:
			---------------------------------------------------------------------------------------------------------
			Bus 001 Device 004: ID 0a5c:5801 Broadcom Corp. BCM5880 Secure Applications Processor with fingerprint swipe sensor
			Bus 001 Device 002: ID 8087:8000 Intel Corp. 
			Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
			Bus 003 Device 002: ID 413c:5534 Dell Computer Corp. 
			Bus 003 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
			Bus 002 Device 012: ID 1a40:0101 Terminus Technology Inc. Hub
			Bus 002 Device 011: ID 1a40:0101 Terminus Technology Inc. Hub
			Bus 002 Device 010: ID 1a40:0101 Terminus Technology Inc. Hub
			Bus 002 Device 009: ID 1a40:0101 Terminus Technology Inc. Hub
			Bus 002 Device 008: ID 413c:2003 Dell Computer Corp. Keyboard
			Bus 002 Device 007: ID 413c:2134 Dell Computer Corp. 
			Bus 002 Device 003: ID 0c45:64d2 Microdia 
			Bus 002 Device 014: ID 03eb:fabe Atmel Corp. 
			Bus 002 Device 013: ID 045e:0040 Microsoft Corp. Wheel Mouse Optical
			Bus 002 Device 006: ID 413c:2513 Dell Computer Corp. internal USB Hub of E-Port Replicator
			Bus 002 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
			---------------------------------------------------------------------------------------------------------
			In this case the dongle is:
				Bus 002 Device 014: ID 03eb:fabe Atmel Corp. 
			From this line you can extract the information necessary.

		Step4: Restart the udev service by opening a terminal and:
			service udev restart


