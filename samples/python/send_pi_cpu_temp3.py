#!/usr/bin/python
"""
// File: send_hearbeat3.py
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
// Copyright (C) 2000-2023
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

send_hearbeat3 host user password [guid]

cron example
* * * * * root cd /root;./.venv/bin/python ./send_heartbeat3.py 192.168.1.7 admin secret FF:FF:FF:FF:FF:FF:FF:FE:60:A4:4C:E7:76:5A:00:00

.venv should have asyncio and telnetlib3 installed

"""


import getpass
import sys
import asyncio
import telnetlib3
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

async def shell(reader, writer):
    rules = [
            ('+OK', 'user admin'),
            ('+OK', 'pass secret'),
            ('+OK', 'send ' + event),
            ('+OK', 'quit'),
            ]

    ruleiter = iter(rules)
    expect, send = next(ruleiter)
    while True:
        outp = await reader.read(1024)
        if not outp:
          break

        if expect in outp:
            writer.write(send)
            writer.write('\r\n')
            try:
                expect, send = next(ruleiter)
            except StopIteration:
                break

        # display all server output
        print(outp, flush=True)

    # EOF
    print()

async def main():
  reader, writer = await telnetlib3.open_connection(host, 9598, shell=shell)
  await writer.protocol.waiter_closed


if __name__ == '__main__':
    asyncio.run(main())