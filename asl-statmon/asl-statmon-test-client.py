#!/usr/bin/python3
#
# Simple client to see that an asl-statmon instance 
# is working properly
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

ap = argparse.ArgumentParser(description="Simple client to see that an asl-statmon instance. Dumps 0MQ messages from the specified port")
ap.add_argument("host", type=str, help="FQDN or IP address of the asl-statmon to test")
ap.add_argument("port", type=int, help="TCP port of asl-statmon to test")
ap.add_argument("--topic", type=str, help="Topic to subscribe to")
args = ap.parse_args()

try:
	print("Creating 0MQ connection to %s:%d" % (args.host,args.port))
	context = zmq.Context()
	socket = context.socket(zmq.SUB)
	socket.connect("tcp://%s:%d" % (args.host, args.port))
	print("Connected. Press CTRL+c to stop...")
	if args.topic:
		socket.setsockopt(zmq.SUBSCRIBE, args.topic.encode("UTF-8"))
	else:
		socket.setsockopt(zmq.SUBSCRIBE, b"")

	while True:
	    message = socket.recv()
	    print("%s" % message.decode("UTF-8"))

except Exception as e:
	print("Error: " + e)
	system.exit(1)
