#!/usr/bin/env python3

# sensorpuck_vscp.py
#
# **Important** 
# This work builds on work done by others but the
# origin of this work is unknown to me so I am unable to give
# credit where it is due.
#
# This file is part of the VSCP (https://www.vscp.org) project
#
# The MIT License (MIT)
#
# Copyright © 2017-2021 Ake Hedman, the VSCP project
# <info@vscp.org>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

from __future__ import print_function
import argparse
import binascii
import os
import sys
from bluepy import btle
from vscp import *
from vscp_class import *
from vscp_type import *
import vscphelper

# Credentials for the remote VSCP  Daemon
VSCP_HOST = "192.168.1.7:9598"
VSCP_USER = "admin"
VSCP_PASSWORD = "secret"

if os.getenv('C', '1') == '0':
    ANSI_RED = ''
    ANSI_GREEN = ''
    ANSI_YELLOW = ''
    ANSI_CYAN = ''
    ANSI_WHITE = ''
    ANSI_OFF = ''
else:
    ANSI_CSI = "\033["
    ANSI_RED = ANSI_CSI + '31m'
    ANSI_GREEN = ANSI_CSI + '32m'
    ANSI_YELLOW = ANSI_CSI + '33m'
    ANSI_CYAN = ANSI_CSI + '36m'
    ANSI_WHITE = ANSI_CSI + '37m'
    ANSI_OFF = ANSI_CSI + '0m'

h1 = -1  # Handle for VSCP session

def dump_services(dev):
    services = sorted(dev.services, key=lambda s: s.hndStart)
    for s in services:
        print("\t%04x: %s" % (s.hndStart, s))
        if s.hndStart == s.hndEnd:
            continue
        chars = s.getCharacteristics()
        for i, c in enumerate(chars):
            props = c.propertiesToString()
            h = c.getHandle()
            if 'READ' in props:
                val = c.read()
                if c.uuid == btle.AssignedNumbers.device_name:
                    string = ANSI_CYAN + '\'' + \
                        val.decode('utf-8') + '\'' + ANSI_OFF
                elif c.uuid == btle.AssignedNumbers.device_information:
                    string = repr(val)
                else:
                    string = '<s' + binascii.b2a_hex(val).decode('utf-8') + '>'
            else:
                string = ''
            print("\t%04x:    %-59s %-12s %s" % (h, c, props, string))

            while True:
                h += 1
                if h > s.hndEnd or (i < len(chars) - 1 and h >= chars[i + 1].getHandle() - 1):
                    break
                try:
                    val = dev.readCharacteristic(h)
                    print("\t%04x:     <%s>" %
                           (h, binascii.b2a_hex(val).decode('utf-8')))
                except btle.BTLEException:
                    break


class ScanPrint(btle.DefaultDelegate):

    def __init__(self, opts):
        btle.DefaultDelegate.__init__(self)
        self.opts = opts

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            status = "new"
        elif isNewData:
            if self.opts.new:
                return
            status = "update"
        else:
            if not self.opts.all:
                return
            status = "old"

        if dev.rssi < self.opts.sensitivity:
            return

        print('    Device (%s): %s (%s), %d dBm %s' %
               (status,
                   ANSI_WHITE + dev.addr + ANSI_OFF,
                   dev.addrType,
                   dev.rssi,
                   ('' if dev.connectable else '(not connectable)'))
               )
        for (sdid, desc, val) in dev.getScanData():
            if sdid in [8, 9]:
                print('\t' + desc + ': \'' + ANSI_CYAN + val + ANSI_OFF + '\'')
            else:
                print('\t' + desc + ': <' + val + '>')
        print('\trow data: ' + val)
        if ( 28 == len(val) and 'aa4a' == val[8:12] ):
            ex = vscpEventEx()
            print("\tDetected %s" % ANSI_GREEN + "SENSORPUCK" + ANSI_OFF )

            # GUID based on Bluetooth MAC
            guid_orig = "FF:FF:FF:FF:FF:FF:FF:F8:" + dev.addr.upper()
            print('\t' + "GUID: %s" % guid_orig + ":00:00" )

            # rssi
            rssi = int(dev.rssi)
            print('\t' + "RSSI: %d dBm" % rssi )
            ex.head = VSCP_PRIORITY_NORMAL | VSCP_HEADER16_DUMB
            ex.obid = 0
            ex.timestamp = 0
            guid_array = (guid_orig+':00:08').split(':')
            pos = 0
            for x in guid_array:
                ex.guid[pos] = int(x,16)
                pos += 1
            ex.vscpclass = VSCP_CLASS1_DATA
            ex.vscptype = VSCP_TYPE_DATA_SIGNAL_QUALITY
            # data coding + unit (dBm) + sensor index
            ex.data[0] = VSCP_DATACODING_INTEGER + \
                (0x02 << 3) + \
                0x00
            ex.data[1] = rssi                      # One byte data value
            ex.sizedata = 2
            rv =vscphelper.sendEventEx(h1,ex)
            if VSCP_ERROR_SUCCESS != rv :
                vscphelper.closeSession(h1)
                raise ValueError('Command error: sendEventEx  Error code=%d' % rv )
            print("\t\tSent RSSI event")
            guid_array = (guid_orig+':00:01').split(':')
            pos = 0
            for x in guid_array:
                ex.guid[pos] = int(x,16)
                pos += 1

            # Humidity
            low = val[12:14]
            high = val[14:16]
            humidity = float(int(high,16)*256 + int(low,16))
            humidity = humidity/10
            print('\t' + 'Relative humidity: ' + str(humidity) +'%')
            ex.head = VSCP_PRIORITY_NORMAL | VSCP_HEADER16_DUMB
            ex.obid = 0
            ex.timestamp = 0
            guid_array = (guid_orig+':00:02').split(':')
            pos = 0
            for x in guid_array:
                ex.guid[pos] = int(x,16)
                pos += 1
            ex.vscpclass = VSCP_CLASS2_MEASUREMENT_STR
            ex.vscptype = VSCP_TYPE_MEASUREMENT_HUMIDITY
            # unit = 0, sensor index = 0
            ex.data[0] = 0  # Sensor index
            ex.data[1] = 0  # Zone = 0
            ex.data[2] = 0  # Sub Zone = 0
            ex.data[3] = 0  # Unit = 0, Relative humidity in percent
            humstr = str(humidity)
            pos = 0
            for c in humstr:
                ex.data[pos+4] = ord(humstr[pos])
                pos += 1
            ex.sizedata = 4 + len(humstr)
            rv =vscphelper.sendEventEx(h1,ex)
            if VSCP_ERROR_SUCCESS != rv :
                vscphelper.closeSession(h1)
                raise ValueError('Command error: sendEventEx  Error code=%d' % rv )
            print("\t\tSent humidity event.")


            # temperature
            low = val[16:18]
            high = val[18:20]
            temp = float(int(high,16)*256 + int(low,16))
            temp = temp/10
            print('\t' + 'Temperature: ' + str(temp) +'C')
            ex.head = VSCP_PRIORITY_NORMAL | VSCP_HEADER16_DUMB
            ex.obid = 0
            ex.timestamp = 0
            guid_array = (guid_orig+':00:01').split(':')
            pos = 0
            for x in guid_array:
                ex.guid[pos] = int(x,16)
                pos += 1
            ex.vscpclass = VSCP_CLASS2_MEASUREMENT_STR
            ex.vscptype = VSCP_TYPE_MEASUREMENT_TEMPERATURE
            # unit = 0, sensor index = 0
            ex.data[0] = 0  # Sensor index                         
            ex.data[1] = 0  # Zone = 0
            ex.data[2] = 0  # Sub Zone = 0
            ex.data[3] = 0  # Unit = 0, Relative humidity in percent
            tempstr = str(temp)
            pos = 0
            for c in tempstr:
                ex.data[pos+4] = ord(tempstr[pos])
                pos += 1
            ex.sizedata = 4 + len(tempstr)
            rv =vscphelper.sendEventEx(h1,ex)
            if VSCP_ERROR_SUCCESS != rv :
                vscphelper.closeSession(h1)
                raise ValueError('Command error: sendEventEx  Error code=%d' % rv )
            print("\t\tSent temperature event")

            # Light intensity
            low = val[20:22]
            high = val[22:24]
            lux = int(high,16)*256 + int(low,16)
            lux = lux*2
            print('\t' + 'Ambient light: ' + str(lux) +'lux')
            ex.head = VSCP_PRIORITY_NORMAL | VSCP_HEADER16_DUMB
            ex.obid = 0
            ex.timestamp = 0
            guid_array = (guid_orig+':00:03').split(':')
            pos = 0
            for x in guid_array:
                ex.guid[pos] = int(x,16)
                pos += 1
            ex.vscpclass = VSCP_CLASS2_MEASUREMENT_STR
            ex.vscptype = VSCP_TYPE_MEASUREMENT_ILLUMINANCE
            # unit = 0, sensor index = 0
            ex.data[0] = 0  # Sensor index
            ex.data[1] = 0  # Zone = 0
            ex.data[2] = 0  # Sub Zone = 0
            ex.data[3] = 0  # Unit = 0, Relative humidity in percent
            luxstr = str(lux)
            pos = 0
            for c in luxstr:
                ex.data[pos+4] = ord(luxstr[pos])
                pos += 1
            ex.sizedata = 4 + len(luxstr)
            rv =vscphelper.sendEventEx(h1,ex)
            if VSCP_ERROR_SUCCESS != rv :
                vscphelper.closeSession(h1)
                raise ValueError('Command error: sendEventEx  Error code=%d' % rv )
            print("\t\tSent light intensity event")


            # UV index
            low = val[24:26]
            uv = int(low,16)
            print('\tUV index: ' + str(uv) )
            ex.head = VSCP_PRIORITY_NORMAL | VSCP_HEADER16_DUMB
            ex.obid = 0
            ex.timestamp = 0
            guid_array = (guid_orig+':00:04').split(':')
            pos = 0
            for x in guid_array:
                ex.guid[pos] = int(x,16)
                pos += 1
            ex.vscpclass = VSCP_CLASS1_WEATHER
            ex.vscptype = VSCP_TYPE_WEATHER_UV_INDEX
            # unit = 0, sensor index = 0
            ex.data[0] = 0   # Zone = 0
            ex.data[1] = 0   # Sub Zone = 0
            ex.data[2] = uv  # UV Index 0-15
            ex.sizedata = 3
            rv =vscphelper.sendEventEx(h1,ex)
            if VSCP_ERROR_SUCCESS != rv :
                pyvscphlp_closeSession(h1)
                raise ValueError('Command error: sendEventEx  Error code=%d' % rv )
            print("\t\tSent light intensity event")



            # Battery voltage
            low = val[26:28]
            voltage = float(int(low,16)) / 10
            print('\t' + 'Battery voltage: ' + str(voltage) +'V')
            ex.head = VSCP_PRIORITY_NORMAL | VSCP_HEADER16_DUMB
            ex.obid = 0
            ex.timestamp = 0
            guid_array = (guid_orig+':00:05').split(':')
            pos = 0
            for x in guid_array:
                ex.guid[pos] = int(x,16)
                pos += 1
            ex.vscpclass = VSCP_CLASS2_MEASUREMENT_STR
            ex.vscptype = VSCP_TYPE_MEASUREMENT_ELECTRICAL_POTENTIAL
            # unit = 0, sensor index = 0
            ex.data[0] = 0  # Sensor index
            ex.data[1] = 0  # Zone = 0
            ex.data[2] = 0  # Sub Zone = 0
            ex.data[3] = 0  # Unit = 0, Relative humidity in percent
            voltagestr = str(voltage)
            pos = 0
            for c in voltagestr:
                ex.data[pos+4] = ord(voltagestr[pos])
                pos += 1
            ex.sizedata = 4 + len(voltagestr)
            rv =vscphelper.sendEventEx(h1,ex)
            if VSCP_ERROR_SUCCESS != rv :
                vscphelper.closeSession(h1)
                raise ValueError('Command error: sendEventEx  Error code=%d' % rv )
            print("\t\tSent voltage event")
        else:
            print('\tUnknown data (Device unknown)')

        if not dev.scanData:
            print ('\t(no data)')
        print('')


def main():
    global h1
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--hci', action='store', type=int, default=0,
            help='Interface number for scan')
    parser.add_argument('-t', '--timeout', action='store', type=int, default=4,
            help='Scan delay, 0 for continuous')
    parser.add_argument('-s', '--sensitivity', action='store', type=int, default=-128,
            help='dBm value for filtering far devices')
    parser.add_argument('-d', '--discover', action='store_true',
            help='Connect and discover service to scanned devices')
    parser.add_argument('-a', '--all', action='store_true',
            help='Display duplicate adv responses, by default show new + updated')
    parser.add_argument('-n', '--new', action='store_true',
            help='Display only new adv responses, by default show new + updated')
    parser.add_argument('-v', '--verbose', action='store_true',
            help='Increase output verbosity')
    parser.add_argument('-c', '--server', action='store', type=str, default='127.0.0.1',  
            help='VSCP server to connect to (default: 127.0.0.1)')
    parser.add_argument('-x', '--port', action='store', type=int, default=9598,
            help='VSCP server port connect to (default:9598)')
    parser.add_argument('-u', '--user', action='store', type=str, default='admin',
            help='User to login as on remote VSCP server (default: admin)')
    parser.add_argument('-p', '--password', action='store', type=str, default='secret',
            help='Password to use for VSCP server (default: secret)')

    arg = parser.parse_args(sys.argv[1:])

    btle.Debugging = arg.verbose

    # New VSCP session
    h1 = vscphelper.newSession()

    if (0 == h1 ):
        vscphelper.closeSession(h1)
        raise ValueError('Unable to open vscphelp library session')

    # Connect to server
    print( "\n\nConnection in progress...")
    rv = vscphelper.open(h1, VSCP_HOST, VSCP_USER, VSCP_PASSWORD)
    if VSCP_ERROR_SUCCESS == rv :
        print("Command success: Connected to VSCP server\n")
    else:
        vscphelper.closeSession(h1)
        raise ValueError('Failed to connect to VSCP server  Error code=%d' % rv )
    scanner = btle.Scanner(arg.hci).withDelegate(ScanPrint(arg))

    print(ANSI_RED + "Scanning for devices..." + ANSI_OFF)
    devices = scanner.scan(arg.timeout)

    if arg.discover:
        print(ANSI_RED + "Discovering services..." + ANSI_OFF)

        for d in devices:
            if not d.connectable or d.rssi < arg.sensitivity:
                continue

            print("    Connecting to", ANSI_WHITE + d.addr + ANSI_OFF + ":")

            dev = btle.Peripheral(d)
            dump_services(dev)
            dev.disconnect()
            print

    rv = vscphelper.close(h1)
    if VSCP_ERROR_SUCCESS != rv :
        print("\nFailed to close connection to VSCP server")
    else :
        print("\nVSCP server connection closed")

    # Clean up VSCP usage
    vscphelper.closeSession(h1)

if __name__ == "__main__":
    main()
