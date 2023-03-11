#!/usr/bin/python3
#
# Simple client to asl-cmdlink
# is working properly
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE

#

import argparse
import signal
import sys
import zmq

def sigterm_handler(_signo, _stack_frame):
	print("exiting on signal %d" % (_signo))
	socket.close()
	sys.exit(0)

signal.signal(signal.SIGINT, sigterm_handler)
signal.signal(signal.SIGHUP, sigterm_handler)
signal.signal(signal.SIGTERM, sigterm_handler)

ap = argparse.ArgumentParser(description="Simple client to see that an asl-cmdlink instance. Dumps 0MQ messages from the specified port")
ap.add_argument("host", type=str, help="FQDN or IP address of the asl-cmdlink to test")
ap.add_argument("port", type=int, help="TCP port of asl-cmdlink to test")
ap.add_argument("cmd", type=str, help="Command to execute enclosed in double quotes")
args = ap.parse_args()

try:
	print("Creating 0MQ connection to %s:%d" % (args.host,args.port))
	context = zmq.Context()
	client = context.socket(zmq.REQ)
	client.connect("tcp://%s:%d" % (args.host, args.port))
	print("Connected. Press CTRL+c to stop...")

	client.send(args.cmd.encode("UTF-8"))

	if( client.poll(2500) & zmq.POLLIN ) != 0:
		message = client.recv()
		print("+---")
		print(message.decode("UTF-8"))
		print("+---")

	client.setsockopt(zmq.LINGER,0)
	client.close()

except Exception as e:
	print(e)
	sys.exit(1)
