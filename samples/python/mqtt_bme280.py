#!/usr/bin/python3
# --------------------------------------
#    ___  ___  _ ____
#   / _ \/ _ \(_) __/__  __ __
#  / , _/ ___/ /\ \/ _ \/ // /
# /_/|_/_/  /_/___/ .__/\_, /
#                /_/   /___/
#
#           bme280.py
#  Read data from a digital pressure sensor.
#
#  Official datasheet available from :
#  https://www.bosch-sensortec.com/bst/products/all_products/bme280
#
# Author : Matt Hawkins
# Date   : 21/01/2018
#
# https://www.raspberrypi-spy.co.uk/
#
# --------------------------------------

# Changes and additions for VSCP © 2021 Ake Hedman, Grodans Paradis AB <info@grodansparadis.com>
# File is part of the VSCP project https://www.vscp.org

import configparser
import getopt
import json
import math
import sys
import time
from ctypes import c_byte, c_short, c_ubyte

import paho.mqtt.client as mqtt
import smbus
import vscp
import vscp_class as vc
import vscp_type as vt

BMP180_CHIP_ID = 0x55 // 85
BMP280_CHIP_ID = 0x58 // 88
BME280_CHIP_ID = 0x60 // 96
BME280_SOFT_RESET_VAL = 0x86

DEVICE = 0x76  # Default device I2C address

# ----------------------------------------------------------------------------
#                              C O N F I G U R E
# ----------------------------------------------------------------------------

# change this to match the location's pressure (hPa) at sea level
sea_level_pressure = 1013.25

# Print some info along the way
bVerbose = False

# Print debug info if true
bDebug = False

# Subtract this value from reported temperature
temp_corr = 0.0

# Height at installation  location
height_at_location = 0.0

# GUID for sensors (Ethernet MAC used if empty)
# Should normally have two LSB's set to zero for sensor id use
guid = ""

# MQTT broker
host = "192.168.1.7"

# MQTT broker port
port = 1883

# Username to login at server
user = "vscp"

# Password to login at server
password = "secret"

# MQTT publish topic.
#   %guid% is replaced with GUID
#   %class% is replaced with event class
#   %type% is replaced with event type
topic = "vscp/{xguid}/{xclass}/{xtype}/{xsensorindex}"

# Sensor index for sensors (BME280)
# Default is to use GUID to identify sensor
sensorindex_temperature = 0
sensorindex_humidity = 1
sensorindex_pressure = 2
sensorindex_pressure_adj = 3
sensorindex_altitude = 4
sensorindex_dewpoint = 5

# Zone for module
zone = 0

# Subzone for module
subzone = 0

# Last two bytes for GUID is made up of number
# given here on the form MSB:LSB
id_temperature = 0
id_humidity = 1
id_pressure = 2
id_pressure_adj = 3
id_altitude = 4
id_dewpoint = 5

note_temperature = "Temperature from BME280"
note_humidity = "Humidity from BME280"
note_pressure = "Pressure from BME280"
note_pressure_adj = "Sea level pressure from BME280"
note_altitude = "Altitude from BME280"
note_dewpoint = "Dewpoint from BME280"

# Configuration will be read from path set here
cfgpath = ""

# ----------------------------------------------------------------------------------------

config = configparser.ConfigParser()

bus = smbus.SMBus(1)  # Rev 2 Pi, Pi 2 & Pi 3 uses bus 1
                     # Rev 1 Pi uses bus 0


def usage():
    print("usage: mqtt-bm280.py -v -c <pat-to-config-file> -h ")
    print("---------------------------------------------")
    print("-h/--help    - This text.")
    print("-v/--verbose - Print output also to screen.")
    print("-c/--config  - Path to configuration file.")


def getShort(data, index):
  # return two bytes from data as a signed 16-bit value
  return c_short((data[index+1] << 8) + data[index]).value


def getUShort(data, index):
  # return two bytes from data as an unsigned 16-bit value
  return (data[index+1] << 8) + data[index]


def getChar(data, index):
  # return one byte from data as a signed char
  result = data[index]
  if result > 127:
    result -= 256
  return result


def getUChar(data, index):
  # return one byte from data as an unsigned char
  result = data[index] & 0xFF
  return result


def readBME280ID(addr=DEVICE):
  # Chip ID Register Address
  REG_ID = 0xD0
  (chip_id, chip_version) = bus.read_i2c_block_data(addr, REG_ID, 2)
  return (chip_id, chip_version)


def readBME280All(addr=DEVICE):
  # Register Addresses
  REG_DATA = 0xF7
  REG_CONTROL = 0xF4
  REG_CONFIG = 0xF5

  REG_CONTROL_HUM = 0xF2
  REG_HUM_MSB = 0xFD
  REG_HUM_LSB = 0xFE

  # Oversample setting - page 27
  OVERSAMPLE_TEMP = 2
  OVERSAMPLE_PRES = 2
  MODE = 1

  # Oversample setting for humidity register - page 26
  OVERSAMPLE_HUM = 2
  bus.write_byte_data(addr, REG_CONTROL_HUM, OVERSAMPLE_HUM)

  control = OVERSAMPLE_TEMP << 5 | OVERSAMPLE_PRES << 2 | MODE
  bus.write_byte_data(addr, REG_CONTROL, control)

  # Read blocks of calibration data from EEPROM
  # See Page 22 data sheet
  cal1 = bus.read_i2c_block_data(addr, 0x88, 24)
  cal2 = bus.read_i2c_block_data(addr, 0xA1, 1)
  cal3 = bus.read_i2c_block_data(addr, 0xE1, 7)

  # Convert byte data to word values
  dig_T1 = getUShort(cal1, 0)
  dig_T2 = getShort(cal1, 2)
  dig_T3 = getShort(cal1, 4)

  dig_P1 = getUShort(cal1, 6)
  dig_P2 = getShort(cal1, 8)
  dig_P3 = getShort(cal1, 10)
  dig_P4 = getShort(cal1, 12)
  dig_P5 = getShort(cal1, 14)
  dig_P6 = getShort(cal1, 16)
  dig_P7 = getShort(cal1, 18)
  dig_P8 = getShort(cal1, 20)
  dig_P9 = getShort(cal1, 22)

  dig_H1 = getUChar(cal2, 0)
  dig_H2 = getShort(cal3, 0)
  dig_H3 = getUChar(cal3, 2)

  dig_H4 = getChar(cal3, 3)
  dig_H4 = (dig_H4 << 24) >> 20
  dig_H4 = dig_H4 | (getChar(cal3, 4) & 0x0F)

  dig_H5 = getChar(cal3, 5)
  dig_H5 = (dig_H5 << 24) >> 20
  dig_H5 = dig_H5 | (getUChar(cal3, 4) >> 4 & 0x0F)

  dig_H6 = getChar(cal3, 6)

  # Wait in ms (Datasheet Appendix B: Measurement time and current calculation)
  wait_time = 1.25 + (2.3 * OVERSAMPLE_TEMP) + ((2.3 *
                      OVERSAMPLE_PRES) + 0.575) + ((2.3 * OVERSAMPLE_HUM)+0.575)
  time.sleep(wait_time/1000)  # Wait the required time

  # Read temperature/pressure/humidity
  data = bus.read_i2c_block_data(addr, REG_DATA, 8)
  pres_raw = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
  temp_raw = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
  hum_raw = (data[6] << 8) | data[7]

  # Refine temperature
  var1 = ((((temp_raw >> 3)-(dig_T1 << 1)))*(dig_T2)) >> 11
  var2 = (((((temp_raw >> 4) - (dig_T1)) *
          ((temp_raw >> 4) - (dig_T1))) >> 12) * (dig_T3)) >> 14
  t_fine = var1+var2
  temperature = float(((t_fine * 5) + 128) >> 8);

  # Refine pressure and adjust for temperature
  var1 = t_fine / 2.0 - 64000.0
  var2 = var1 * var1 * dig_P6 / 32768.0
  var2 = var2 + var1 * dig_P5 * 2.0
  var2 = var2 / 4.0 + dig_P4 * 65536.0
  var1 = (dig_P3 * var1 * var1 / 524288.0 + dig_P2 * var1) / 524288.0
  var1 = (1.0 + var1 / 32768.0) * dig_P1
  if var1 == 0:
    pressure = 0
  else:
    pressure = 1048576.0 - pres_raw
    pressure = ((pressure - var2 / 4096.0) * 6250.0) / var1
    var1 = dig_P9 * pressure * pressure / 2147483648.0
    var2 = pressure * dig_P8 / 32768.0
    pressure = pressure + (var1 + var2 + dig_P7) / 16.0

  # Refine humidity
  humidity = t_fine - 76800.0
  humidity = (hum_raw - (dig_H4 * 64.0 + dig_H5 / 16384.0 * humidity)) * (dig_H2 / 65536.0 *
              (1.0 + dig_H6 / 67108864.0 * humidity * (1.0 + dig_H3 / 67108864.0 * humidity)))
  humidity = humidity * (1.0 - dig_H1 * humidity / 524288.0)
  if humidity > 100:
    humidity = 100
  elif humidity < 0:
    humidity = 0

  return temperature/100.0, pressure/100.0, humidity

# def main():


# ----------------------------------------------------------------------------

args = sys.argv[1:]
nargs = len(args)

try:
   opts, args = getopt.getopt(args, "hvc:", ["help", "verbose", "config="])
except getopt.GetoptError:
   print("unrecognized format!")
   usage()
   sys.exit(2)

for opt, arg in opts:
  if opt in ("-h", "--help"):
      print("HELP")
      usage()
      sys.exit()
  elif opt in ("-v", "--verbose"):
      bVerbose = True
  elif opt in ("-c", "--config"):
      cfgpath = arg

if (len(cfgpath)):

  init = config.read(cfgpath)

  # ----------------- GENERAL -----------------
  if 'bVerbose' in config['GENERAL']:
	  bVerbose = config.getboolean('GENERAL', 'bVerbose')
	  if bVerbose:
	      print('Verbose mode enabled.')
	      print('READING CONFIGURATION')
	      print('---------------------')

	# ----------------- VSCP -----------------
  if 'guid' in config['VSCP']:
	  guid = config['VSCP']['guid']
	  if bVerbose:
	    print("guid =", guid)

  if 'sensorindex_temperature' in config['VSCP']:
	  sensorindex_temperature = int(config['VSCP']['sensorindex_temperature'])
	  if bVerbose:
	    print("sensorindex_temperature =", sensorindex_temperature)

  if 'sensorindex_humidity' in config['VSCP']:
	  sensorindex_humidity = int(config['VSCP']['sensorindex_humidity'])
	  if bVerbose:
	    print("sensorindex_humidity =", sensorindex_humidity)
  
  if 'sensorindex_pressure' in config['VSCP']:
	  sensorindex_pressure = int(config['VSCP']['sensorindex_pressure'])
	  if bVerbose:
	    print("sensorindex_pressure =", sensorindex_pressure)

  if 'sensorindex_pressure_adj' in config['VSCP']:
	  sensorindex_pressure_adj = int(config['VSCP']['sensorindex_pressure_adj'])
	  if bVerbose:
	    print("sensorindex_pressure_adj =", sensorindex_pressure_adj)

  if 'sensorindex_gas' in config['VSCP']:
	  sensorindex_gas = int(config['VSCP']['sensorindex_gas'])
	  if bVerbose:
	    print("sensorindex_gas =", sensorindex_gas)

  if 'sensorindex_altitude' in config['VSCP']:
	  sensorindex_altitude = int(config['VSCP']['sensorindex_altitude'])
	  if bVerbose:
	     print("sensorindex_altitude =", sensorindex_altitude)

  if 'sensorindex_dewpoint' in config['VSCP']:
	  sensorindex_dewpoint = int(config['VSCP']['sensorindex_dewpoint'])
	  if bVerbose:
	    print("sensorindex_dewpoint =", sensorindex_dewpoint)

  if 'zone' in config['VSCP']:
	  zone = int(config['VSCP']['zone'])
	  if bVerbose:
	    print("zone =", zone)

  if 'subzone' in config['VSCP']:
	  subzone = int(config['VSCP']['subzone'])
	  if bVerbose:
	    print("subzone =", subzone)

  if 'id_temperature' in config['VSCP']:
	  id_temperature = int(config['VSCP']['id_temperature'])
	  if bVerbose:
	    print("id_temperature =", id_temperature)

  if 'id_humidity' in config['VSCP']:
	  id_humidity = int(config['VSCP']['id_humidity'])
	  if bVerbose:
	    print("id_humidity =", id_humidity)

  if 'id_pressure' in config['VSCP']:
	  id_pressure = int(config['VSCP']['id_pressure'])
	  if bVerbose:
	    print("id_pressure =", id_pressure)

  if 'id_pressure_adj' in config['VSCP']:
	  id_pressure_adj = int(config['VSCP']['id_pressure_adj'])
	  if bVerbose:
	    print("id_pressure_adj =", id_pressure_adj)

  if 'id_gas' in config['VSCP']:
	  id_gas = int(config['VSCP']['id_gas'])
	  if bVerbose:
	    print("id_gas =", id_gas)

  if 'id_altitude' in config['VSCP']:
	  id_altitude = int(config['VSCP']['id_altitude'])
	  if bVerbose:
	    print("id_altitude =", id_altitude)

  if 'id_dewpoint' in config['VSCP']:
	  id_dewpoint = int(config['VSCP']['id_dewpoint'])
	  if bVerbose:
	    print("id_dewpoint =", id_dewpoint)

# ----------------- MQTT -----------------
  if 'host' in config['MQTT']: 
	  host = config['MQTT']['host']
	  if bVerbose:
	    print("host =", host)

  if 'port' in config['MQTT']:
	  port = int(config['MQTT']['port'])
	  if bVerbose:
	    print("port =", port)

  if 'user' in config['MQTT']:
	  user = config['MQTT']['user']
	  if bVerbose:
	    print("user =", user)

  if 'password' in config['MQTT']:
	  password = config['MQTT']['password']
	  if bVerbose:
	    print("password =", "***********")
	    # print("password =", password)

  if 'topic' in config['MQTT']:
	  topic = config['MQTT']['topic']
	  if bVerbose:
	    print("topic =", password)

  if 'note_temperature' in config['MQTT']:
	  note_temperature = config['MQTT']['note_temperature']
	  if bVerbose:
	    print("note_temperature =", note_temperature)

  if 'note_humidity' in config['MQTT']:
	  note_humidity = config['MQTT']['note_humidity']
	  if bVerbose:
	    print("note_humidity =", note_humidity)

  if 'note_pressure' in config['MQTT']:
	  note_pressure = config['MQTT']['note_pressure']
	  if bVerbose:
	    print("note_pressure =", note_pressure)

  if 'note_pressure_adj' in config['MQTT']:
	  note_pressure_adj = config['MQTT']['note_pressure_adj']
	  if bVerbose:
	    print("note_pressure_adj =", note_pressure_adj)

  if 'note_gas' in config['MQTT']:
	  note_gas = config['MQTT']['note_gas']
	  if bVerbose:
	    print("note_gas =", note_gas)

  if 'note_altitude' in config['MQTT']:
	  note_altitude = config['MQTT']['note_altitude']
	  if bVerbose:
	    print("note_altitude =", note_altitude)

  if 'note_dewpoint' in config['MQTT']:
	  note_dewpoint = config['MQTT']['note_dewpoint']
	  if bVerbose:
	    print("note_dewpoint =", note_dewpoint)

	# ----------------- BME280 -----------------

  if 'sea_level_pressure' in config['BME280']:
	  if not bDebug :
	    sea_level_pressure = float(config['BME280']['sea_level_pressure'])
	  if bVerbose:
	    print("sea_level_pressure =", float(config['BME280']['sea_level_pressure']))

  if 'temp_corr' in config['BME280']:
	  if not bDebug :
	    temp_corr = float(config['BME280']['temp_corr'])
	  if bVerbose:
	    print("temp_corr =", temp_corr)

  if 'height_at_location' in config['BME280']:
	  if not bDebug :
	    height_at_location = float(config['BME280']['height_at_location'])       
	  if bVerbose:
	    print("height_at_location =", height_at_location)

# -----------------------------------------------------------------------------

# define message callback
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))

# define connect callback
def on_connect(client, userdata, flags, rc):
    print("Connected =",str(rc))

# define publish callback
def on_publish(client, userdata, result):
    print("Publish callback\n", result)

# -----------------------------------------------------------------------------

client= mqtt.Client()

# bind callback function
client.on_message=on_connect
client.on_message=on_message
client.on_message=on_publish

client.username_pw_set(user, password)

if bVerbose :
	print("\n\nConnection in progress...", host, port)

client.connect(host,port)

client.loop_start()     # start loop to process received messages

# -----------------------------------------------------------------------------

# Initialize VSCP event content
def initEvent(ex,id,vscpClass,vscpType):
	# Dumb node, priority normal
	ex.head = vscp.VSCP_PRIORITY_NORMAL | vscp.VSCP_HEADER16_DUMB
	g = vscp.guid()
	if ("" == guid):
	  g.setFromString(guid)
	else :
	  g.setGUIDFromMAC(id)
	  ex.guid = g.guid
	  ex.vscpclass = vscpClass
	  ex.vscptype = vscpType
	return g

# -----------------------------------------------------------------------------

# Read sensor id etc
(chip_id, chip_version) = readBME280ID()

if bVerbose :
  print("-------------------------------------------------------------------------------")
  print("Sending events...")
  print( "Chip ID     : %d" % chip_id)
  print( "Version     : %d" % chip_version)

temperature,pressure,humidity = readBME280All()

# -----------------------------------------------------------------------------
#                           T E M P E R A T U R E
# -----------------------------------------------------------------------------

temperature_str = "{:0.2f}".format(temperature - temp_corr)

if bVerbose :
	print( "Temperature : %0.2f C" % (temperature - temp_corr))

ex = vscp.vscpEventEx()
g = initEvent(ex, id_temperature, vc.VSCP_CLASS2_MEASUREMENT_STR, vt.VSCP_TYPE_MEASUREMENT_TEMPERATURE)

# Size is predata + string length + terminating zero
ex.sizedata = 4 + len(temperature_str) + 1
ex.data[0] = sensorindex_temperature
ex.data[1] = zone
ex.data[2] = subzone
ex.data[3] = 1  # unit is degrees Celsius
b = temperature_str.encode()
for idx in range(len(b)):
  ex.data[idx + 4] = b[idx]
ex.data[4 + len(temperature_str)] = 0  # optional terminating zero

j = ex.toJSON()
j["vscpNote"] = note_temperature
# Add extra measurement information
j["measurement"] = { 
  "value" : temperature,
  "unit" : 1,
  "sensorindex" : sensorindex_temperature,
  "zone" : zone,
  "subzone" : subzone
}

ptopic = topic.format( xguid=g.getAsString(), xclass=ex.vscpclass, xtype=ex.vscptype, xsensorindex=sensorindex_temperature)
if ( len(ptopic) ):
  rv = client.publish(ptopic, json.dumps(j))
  if 0 != rv[0] :
    print("Failed to pressure rv=", rv)

# -----------------------------------------------------------------------------
#                             H U M I D I T Y
# -----------------------------------------------------------------------------

if BME280_CHIP_ID == chip_id:

  humidity_str = "{:0.0f}".format(humidity)

  if bVerbose :
	  print( "Humidity : %f%%" % humidity)

  ex = vscp.vscpEventEx()
  initEvent(ex, id_humidity, vc.VSCP_CLASS2_MEASUREMENT_STR,vt.VSCP_TYPE_MEASUREMENT_HUMIDITY)

  # Size is predata + string length + terminating zero
  ex.sizedata = 4 + len(humidity_str) + 1
  ex.data[0] = sensorindex_humidity
  ex.data[1] = zone
  ex.data[2] = subzone
  ex.data[3] = 0  # default unit % of moisture
  b = humidity_str.encode()
  for idx in range(len(b)):
    ex.data[idx + 4] = b[idx]
  ex.data[4 + len(humidity_str)] = 0  # optional terminating zero

  j = ex.toJSON()
  j["vscpNote"] = note_humidity
  # Add extra measurement information
  j["measurement"] = { 
    "value" : humidity,
    "unit" : 0,
    "sensorindex" : sensorindex_humidity,
    "zone" : zone,
    "subzone" : subzone
  }

  ptopic = topic.format( xguid=g.getAsString(), xclass=ex.vscpclass, xtype=ex.vscptype, xsensorindex=sensorindex_humidity)
  if ( len(ptopic) ):
    rv = client.publish(ptopic, json.dumps(j))
    if 0 != rv[0] :
        print("Failed to pressure rv=", rv)

# -----------------------------------------------------------------------------
#                             P R E S S U R E
# -----------------------------------------------------------------------------

pressure = pressure
pressure_str = "{:0.2f}".format(pressure)

if bVerbose :
  print( "Pressure : %0.2f hPa" % pressure)
  print(pressure_str)

ex = vscp.vscpEventEx()
initEvent(ex, id_pressure, vc.VSCP_CLASS2_MEASUREMENT_STR,vt.VSCP_TYPE_MEASUREMENT_PRESSURE)

# Size is predata + string length + terminating zero
ex.sizedata = 4 + len(pressure_str) + 1
ex.data[0] = sensorindex_pressure
ex.data[1] = zone
ex.data[2] = subzone
ex.data[3] = 0  # default unit Pascal
b = pressure_str.encode()
for idx in range(len(b)):
  ex.data[idx + 4] = b[idx]
ex.data[4 + len(pressure_str)] = 0  # optional terminating zero

j = ex.toJSON()
j["vscpNote"] = note_pressure
# Add extra pressure information
j["measurement"] = { 
  "value" : round(pressure,2),
  "unit" : 0,
  "sensorindex" : sensorindex_pressure,
  "zone" : zone,
  "subzone" : subzone
}

ptopic = topic.format( xguid=g.getAsString(), xclass=ex.vscpclass, xtype=ex.vscptype, xsensorindex=sensorindex_pressure)
if ( len(ptopic) ):
  rv = client.publish(ptopic, payload=json.dumps(j), qos=1)
  if 0 != rv[0] :
      print("Failed to pressure rv=", rv)

# -----------------------------------------------------------------------------
#                           Adjusted Pressure
# -----------------------------------------------------------------------------

pressure_adj_str = "{:f}".format((pressure + height_at_location/8.3))

if bVerbose :
	print( "Adjusted pressure : %0.2f hPa" % float(pressure_adj_str))

ex = vscp.vscpEventEx()
initEvent(ex, id_pressure_adj, vc.VSCP_CLASS2_MEASUREMENT_STR, vt.VSCP_TYPE_MEASUREMENT_PRESSURE)

# Size is predata + string length + terminating zero
ex.sizedata = 4 + len(pressure_adj_str) + 1
ex.data[0] = sensorindex_pressure_adj
ex.data[1] = zone
ex.data[2] = subzone
ex.data[3] = 0  # default unit Pascal
b = pressure_adj_str.encode()
for idx in range(len(b)):
  ex.data[idx + 4] = b[idx]
ex.data[4 + len(pressure_adj_str)] = 0  # optional terminating zero

j = ex.toJSON()
j["vscpNote"] = note_pressure_adj
# Add extra pressure information
j["measurement"] = {
  "value" : round(float(float(pressure_adj_str)),2),
  "unit" : 0,
  "sensorindex" : sensorindex_pressure_adj,
  "zone" : zone,
  "subzone" : subzone
}

#print(json.dumps(j))
ptopic = topic.format( xguid=g.getAsString(), xclass=ex.vscpclass, xtype=ex.vscptype, xsensorindex=sensorindex_pressure_adj)
if ( len(ptopic) ):
  rv = client.publish(ptopic, json.dumps(j))
  if 0 != rv[0] :
      print("Failed to send sea level pressure rv=", rv)

# -----------------------------------------------------------------------------
#                               Dewpoint
# -----------------------------------------------------------------------------

if BME280_CHIP_ID == chip_id:

  dewpoint = temperature - ((100 - humidity) / 5)
  dewpoint_str = "{:0.2f}".format(dewpoint)

  if bVerbose :
	  print( "Dewpoint : %f C" % dewpoint)

  ex = vscp.vscpEventEx()
  initEvent(ex, id_dewpoint, vc.VSCP_CLASS2_MEASUREMENT_STR,vt.VSCP_TYPE_MEASUREMENT_DEWPOINT)

  # Size is predata + string length + terminating zero
  ex.sizedata = 4 + len(dewpoint) + 1
  ex.data[0] = sensorindex_dewpoint
  ex.data[1] = zone
  ex.data[2] = subzone
  ex.data[3] = 0  # default unit Pascal
  b = pressure_str.encode()
  for idx in range(len(b)):
    ex.data[idx + 4] = b[idx]
  ex.data[4 + len(dewpoint)] = 0  # optional terminating zero

  j = ex.toJSON()
  j["vscpNote"] = note_dewpoint
  # Add extra pressure information
  j["measurement"] = {
    "value" : float(dewpoint),
    "unit" : 0,
    "sensorindex" : sensorindex_dewpoint,
    "zone" : zone,
    "subzone" : subzone
  }

  ptopic = topic.format( xguid=g.getAsString(), xclass=ex.vscpclass, xtype=ex.vscptype, xsensorindex=sensorindex_dewpoint)
  if ( len(ptopic) ):
    rv = client.publish(ptopic, json.dumps(j))
    if 0 != rv[0] :
        print("Failed to pressure rv=", rv)

# -----------------------------------------------------------------------------


#time.sleep(0.5)
client.loop_stop()
client.disconnect()


if bVerbose :
    print("-------------------------------------------------------------------------------")
    print("Closed")

# if __name__=="__main__":
#   main()
