#!/usr/bin/python2
"""
// File: send_pi_cpu_temp.py
//
// Usage: send_pi_cpu_temp host user password [guid]
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
// cat /sys/class/thermal/thermal_zone0/temp
"""

import getpass
import sys
import telnetlib
import sys

if ( len(sys.argv) < 4 ):
	sys.exit("Wrong number of parameters - aborting")

guid = "-"
host = sys.argv[1]
user = sys.argv[2]
password = sys.argv[3]
if ( len(sys.argv) > 3 ):
    guid = sys.argv[4]

f = open('/sys/class/thermal/thermal_zone0/temp', 'r')
temperature = f.readline();
tempfloat = float( temperature )/1000;

# Connect to VSCP daemon
tn = telnetlib.Telnet(host, 9598)
tn.read_until("+OK",2)

# Login
tn.write("user " + user + "\n")
tn.read_until("+OK", 2)

tn.write("pass " + password + "\n")
tn.read_until("+OK - Success.",2)

event = "3,"		# Priority=normal
event += "10,6,"	# Temperature measurement class=10, type=6
event += ","		# DateTime is set to current bu VSCP daemon
event += "0,"		# Use interface timestamp
event += "0,"  		# Use obid of interface
event += guid  + ","	# add GUID to event

# datacoding = String format| Celsius | sensor 0
datacoding = 0x40 | (1<<3) | 0  
event += hex(datacoding)	# Add datacoding byte to event

# Make sure length is OK (max seven characters)
tempstr = str( tempfloat )
tempstr = tempstr.strip()
if ( len(tempstr) > 7 ):
    tempstr = tempstr[0:7]

# Write temperature into the event (not line breaks)
for ch in tempstr:
    event += ","
    event += hex(ord(ch))

# Send event to server
tn.write("send " + event + "\n")
tn.read_until("+OK - Success.",2)

tn.write("quit\n")

