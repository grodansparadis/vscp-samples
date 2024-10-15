#!/usr/bin/python
"""
// File: send_file_measurement.py
//
// Usage: echo 1.45 | send_file_measurement.py host user password guid type unit sensorindex zone subzone
// class is always = 1040 (str measurement)
//
// Described here https://github.com/grodansparadis/vscp-samples/tree/master/samples/python
//
// This program is free software; you can redistribute it and/or
// modify it under the terms of the GNU General Public License
// as published by the Free Software Foundation; either version
// 2 of the License, or (at your option) any later version.
//
// This file is part of the VSCP (http://www.vscp.org)
//
// Copyright (C) 2000-2021
// Ake Hedman, Grodans Paradis AB, <akhe@grodansparadis.com>
//
// This file is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this file see the file COPYING.  If not, write to
// the Free Software Foundation, 59 Temple Place - Suite 330,
// Boston, MA 02111-1307, USA.
//
// LOG_FORMAT "%R %.2C"
//

"""

import getpass
import sys
import telnetlib

# host user password guid type unit sensorindex zone, subzone
if ( len(sys.argv) < 6 ):
    sys.exit("Wrong number of parameters - aborting")

host = sys.argv[1]
user = sys.argv[2]
password = sys.argv[3]
guid = sys.argv[4]
type = sys.argv[5]

unit = 0
if ( len(sys.argv) > 6 ):
    unit = sys.argv[6]

sensorindex = 0
if ( len(sys.argv) > 7 ):
    sensorindex = sys.argv[7]

zone = 0
if ( len(sys.argv) > 8 ):
    zone = sys.argv[8]

subzone = 0
if ( len(sys.argv) > 9 ):
    subzone = sys.argv[9]



# Conncet to VSCP daemon
tn = telnetlib.Telnet(host, 9598)
tn.read_until("+OK".encode('ascii'),2)

# Login
tn.write("user " .encode('ascii') + user.encode('ascii') + "\n".encode('ascii'))
tn.read_until("+OK".encode('ascii'), 2)

tn.write("pass " .encode('ascii') + password .encode('ascii') + "\n".encode('ascii'))

tn.read_until("+OK - Success.".encode('ascii'),2)

# For each line from piped digitemp output
for line in sys.stdin:

    strvalue = line;

    event = "3,"		# Priority=normal
    event += "1040,"		# Level II measurement (string)
    event += type + ","		# Event type
    event += ","		# DateTime
    event += "0,"		# Use interface timestamp
    event += "0,"  		# Use obid of interface
    event += guid 		# add GUID to event

    # Write temperature into the event (not line breaks)
    for ch in strvalue:
        if  ( ( 0x0a != ord(ch) ) and ( 0x0d != ord(ch) ) ):
            event += ","
            event += hex(ord(ch)) 

    # Send event to server
    print("event=" + event)
    tn.write("send " .encode('ascii') + event .encode('ascii') + "\n".encode('ascii')) 
    tn.read_until("+OK - Success.".encode('ascii'),2)

tn.write("quit\n".encode('ascii'))

