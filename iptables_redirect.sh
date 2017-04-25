#!/bin/bash

#
#   This script maps the privlidged MODBUS port 502 to the non-privlidged
#   port 10502 so server applications don't have to run with elevated
#   privileges.
#

sudo iptables -t nat -I PREROUTING -p tcp --dport 502 -j REDIRECT --to-ports 10502

