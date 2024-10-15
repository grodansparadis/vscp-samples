#!/usr/bin/python
#---------------------------------------------------------------------
#    ___  ___  _ ____
#   / _ \/ _ \(_) __/__  __ __
#  / , _/ ___/ /\ \/ _ \/ // /
# /_/|_/_/  /_/___/ .__/\_, /
#                /_/   /___/
#
#           bh1750.py
# Read data from a BH1750 digital light sensor.
#
# Author : Matt Hawkins
# Date   : 26/06/2018
#
# For more information please visit :
# https://www.raspberrypi-spy.co.uk/?s=bh1750
#
#---------------------------------------------------------------------

# vscp_bh1750.py
# Adoptions for the VSCP project by Ake Hedman, 2021-09-07
# https://www.vscp.org
# 

import smbus
import time
import getpass
import sys
import telnetlib

# Define some constants from the datasheet

DEVICE     = 0x23 # Default device I2C address

POWER_DOWN = 0x00 # No active state
POWER_ON   = 0x01 # Power on
RESET      = 0x07 # Reset data register value

# Start measurement at 4lx resolution. Time typically 16ms.
CONTINUOUS_LOW_RES_MODE = 0x13
# Start measurement at 1lx resolution. Time typically 120ms
CONTINUOUS_HIGH_RES_MODE_1 = 0x10
# Start measurement at 0.5lx resolution. Time typically 120ms
CONTINUOUS_HIGH_RES_MODE_2 = 0x11
# Start measurement at 1lx resolution. Time typically 120ms
# Device is automatically set to Power Down after measurement.
ONE_TIME_HIGH_RES_MODE_1 = 0x20
# Start measurement at 0.5lx resolution. Time typically 120ms
# Device is automatically set to Power Down after measurement.
ONE_TIME_HIGH_RES_MODE_2 = 0x21
# Start measurement at 1lx resolution. Time typically 120ms
# Device is automatically set to Power Down after measurement.
ONE_TIME_LOW_RES_MODE = 0x23

#bus = smbus.SMBus(0) # Rev 1 Pi uses 0
bus = smbus.SMBus(1)  # Rev 2 Pi uses 1


# host user password guid sensorindex zone, subzone
if ( len(sys.argv) < 4 ):
    sys.exit("Wrong number of parameters - aborting")

host = sys.argv[1]
user = sys.argv[2]
password = sys.argv[3]

guid = "-"
if ( len(sys.argv) > 4 ):
  guid = sys.argv[4]

unit = 0

sensorindex = 0
if ( len(sys.argv) > 5 ):
    sensorindex = sys.argv[5]

zone = 0
if ( len(sys.argv) > 6 ):
    zone = sys.argv[6]

subzone = 0
if ( len(sys.argv) > 7 ):
    subzone = sys.argv[7]

# Conncet to VSCP daemon
tn = telnetlib.Telnet(host, 9598)
tn.read_until("+OK".encode('ascii'),2)

# Login
tn.write("user " .encode('ascii') + user.encode('ascii') + "\n".encode('ascii'))
tn.read_until("+OK".encode('ascii'), 2)

tn.write("pass " .encode('ascii') + password .encode('ascii') + "\n".encode('ascii'))

tn.read_until("+OK - Success.".encode('ascii'),2)


def convertToNumber(data):
  # Simple function to convert 2 bytes of data
  # into a decimal number. Optional parameter 'decimals'
  # will round to specified number of decimal places.
  result=(data[1] + (256 * data[0])) / 1.2
  return (result)

def readLight(addr=DEVICE):
  # Read data from I2C interface
  data = bus.read_i2c_block_data(addr,CONTINUOUS_HIGH_RES_MODE_2)
  return convertToNumber(data)

def main():

    strvalue = format(readLight(),'.2f') 

    event = "3,"                # Priority=normal
    event += "1040,25,"         # Level II measurement (string), Illuminance    
    event += "0,"               # Use obid of interface
    event += ","                # DateTime
    event += "0,"               # Use interface timestamp
    event += guid + ","         # add GUID to event
    event += str(sensorindex) + ","
    event += str(zone) + ","
    event += str(subzone) + ","
    event += str(unit)

    # Write lux value into the event (not line breaks)
    for ch in strvalue:
        if  ( ( 0x0a != ord(ch) ) and ( 0x0d != ord(ch) ) ):
            event += ","
            event += hex(ord(ch))

    # Send event to server
    print("event=" + event)
    tn.write("send " .encode('ascii') + event .encode('ascii') + "\n".encode('ascii'))
    tn.read_until("+OK - Success.".encode('ascii'),2)

    tn.write("quit\n".encode('ascii'))
#  while True:
#    lightLevel=readLight()
#    print("Light Level : " + format(lightLevel,'.2f') + " lx")
#    time.sleep(0.5)

if __name__=="__main__":
   main()
