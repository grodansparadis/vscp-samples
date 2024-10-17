#!/usr/bin/python3
# --------------------------------------
#    ___  ___  _ ____
#  Read data from a digital pressure sensor.
#
#  Official datasheet available from :
#  https://www.bosch-sensortec.com/bst/products/all_products/bme280
#
#  https://github.com/pimoroni/bme680-python
#
# --------------------------------------

# Changes and additions for VSCP © 2024 Ake Hedman, Grodans Paradis AB <info@grodansparadis.com>
# File is part of the VSCP project https://www.vscp.org

import configparser
import getopt
import json
import math
import sys
import time
from ctypes import c_byte, c_short, c_ubyte

import paho.mqtt.client as mqtt
#import smbus
import bme680
import vscp
import vscp_class as vc
import vscp_type as vt


try:
    sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
except (RuntimeError, IOError):
    sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)

# These oversampling settings can be tweaked to
# change the balance between accuracy and noise in
# the data.

sensor.set_humidity_oversample(bme680.OS_2X)
sensor.set_pressure_oversample(bme680.OS_4X)
sensor.set_temperature_oversample(bme680.OS_8X)
sensor.set_filter(bme680.FILTER_SIZE_3)
#sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

#sensor.set_gas_heater_temperature(320)
#sensor.set_gas_heater_duration(150)
#sensor.select_gas_heater_profile(0)

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
sensorindex_gas = 6

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
id_gas = 6

note_temperature = "Temperature from BME680"
note_humidity = "Humidity from BME680"
note_pressure = "Pressure from BME680"
note_pressure_adj = "Sea level pressure from BME680"
note_altitude = "Altitude from BME680"
note_dewpoint = "Dewpoint from BME680"
note_humidity = "Humidity from BME680"
note_gas = "Gas value from BME-680"

# Configuration will be read from path set here
cfgpath = ""

# ----------------------------------------------------------------------------------------

config = configparser.ConfigParser()


def usage():
    print("usage: mqtt-bm680.py -v -c <pat-to-config-file> -h ")
    print("---------------------------------------------")
    print("-h/--help    - This text.")
    print("-v/--verbose - Print output also to screen.")
    print("-c/--config  - Path to configuration file.")


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

client= mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

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
#(chip_id, chip_version) = readBME280ID()

if bVerbose :
  print("-------------------------------------------------------------------------------")
  print("Sending events...")

  if sensor.get_sensor_data():
    output = '{0:.2f} C,{1:.2f} hPa,{2:.3f} %RH'.format(
                sensor.data.temperature,
                sensor.data.pressure,
                sensor.data.humidity)
    print(output)

    if 1: # & sensor.data.heat.stable:
        gas = sensor.data.gas_resistance
        print('Gas: {0} Ohms'.format(gas))

# -----------------------------------------------------------------------------
#                           T E M P E R A T U R E
# -----------------------------------------------------------------------------

temperature_str = "{:0.2f}".format(sensor.data.temperature - temp_corr)

if bVerbose :
	print( "Temperature : %0.2f C" % (sensor.data.temperature - temp_corr))

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
  "value" : sensor.data.temperature,
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

humidity_str = "{:0.0f}".format(sensor.data.humidity)

if bVerbose :
    print( "Humidity : %f%%" % sensor.data.humidity)

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
    "value" : sensor.data.humidity,
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

pressure = sensor.data.pressure
pressure_str = "{:0.2f}".format(sensor.data.pressure*100) 

if bVerbose :
  print( "Pressure : %0.2f hPa" % sensor.data.pressure)
  #print(pressure_str)

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
  "value" : round(sensor.data.pressure*100,2),
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

pressure_adj = (sensor.data.pressure + height_at_location/8.3)*100
pressure_adj_str = "{:0.2f}".format(pressure_adj)

if bVerbose :
    print("Height at location : ", height_at_location)
    print( "Adjusted pressure : %0.2f hPa" % (float(pressure_adj_str)/100))

ex = vscp.vscpEventEx()
initEvent(ex, id_pressure_adj, vc.VSCP_CLASS2_MEASUREMENT_STR, vt.VSCP_TYPE_MEASUREMENT_PRESSURE)

# Size is predata + string length + terminating zero
ex.sizedata = 4 + len(pressure_adj_str) + 1
ex.data[0] = sensorindex_pressure_adj
ex.data[1] = zone
ex.data[2] = subzone
ex.data[3] = 0  # default unit Pascal
b = pressure_adj_str.encode()
print(len(b),ex.sizedata,pressure_str,pressure_adj_str)
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

dewpoint = sensor.data.temperature - ((100 - sensor.data.humidity) / 5)
dewpoint_str = "{:0.2f}".format(dewpoint)

if bVerbose :
    print( "Dewpoint : %f C" % dewpoint)

ex = vscp.vscpEventEx()
initEvent(ex, id_dewpoint, vc.VSCP_CLASS2_MEASUREMENT_STR,vt.VSCP_TYPE_MEASUREMENT_DEWPOINT)

# Size is predata + string length + terminating zero
ex.sizedata = 4 + len(dewpoint_str) + 1
ex.data[0] = sensorindex_dewpoint
ex.data[1] = zone
ex.data[2] = subzone
ex.data[3] = 0  # default unit Pascal
b = pressure_str.encode()
for idx in range(len(b)):
    ex.data[idx + 4] = b[idx]
ex.data[4 + len(dewpoint_str)] = 0  # optional terminating zero

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
