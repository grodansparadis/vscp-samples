#!/usr/bin/python2
"""
// File: send_hearbeat.py
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

# Connect to VSCP daemon
tn = telnetlib.Telnet(host, 9598)
tn.read_until("+OK",2)

# Login
tn.write("user " + user + "\n")
tn.read_until("+OK", 2)

tn.write("pass " + password + "\n")
tn.read_until("+OK - Success.",2)

event = "3,"		# Priority=normal
event += "20,9,"	# Heartbeat
event += ","		# DateTime set to current by VSCP daemon
event += "0,"		# Use interface timestamp
event += "0,"  		# Use obid of interface
event += guid  + ","	# add GUID to event
event += "0,255,255"    # To all zones/subzones

# Send event to server
tn.write("send " + event + "\n")
tn.read_until("+OK - Success.",2)

tn.write("quit\n")

