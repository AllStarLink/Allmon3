# Allmon3

![GitHub](https://img.shields.io/github/license/AllStarLink/Allmon3)

![Bootstrap](https://img.shields.io/badge/bootstrap-%23563D7C.svg?style=for-the-badge&logo=bootstrap&logoColor=white) ![PHP](https://img.shields.io/badge/php-%23777BB4.svg?style=for-the-badge&logo=php&logoColor=white) ![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

Allmon is the standard web-based montitoring and management for the AllStarLink
application. Allmon3 is the next generation of the venerable Allmon2 that is 
rewritten for performance, scalability, and responsiveness.

## Design Goals
Allmon3 features and functionality shall be governed by the following guidelines:

* Use of modern web responsive design for usability on all device form factors
* Clear separation between long-running tasks and client-based display updates
* Permit reduced workload on potentially slow repeater site links by cleanly supporting the ability to run only the pollers on the device controlling the repeater and run the dashaboard in the cloud; easy prevention of unnecessary web traffic, spidering, etc.
* Prioritization of the common use cases of AllStarLink for feature enhancements

## Community
All code of Allmon3 not otherwise licensed (e.g., Bootstrap, etc.) is licensed
under the [GNU Affero General Public License v3](https://www.gnu.org/licenses/why-affero-gpl.html).
The choice of the AGPLv3 promotes giving back to the amateur radio and
ASL communities.

## Requirements
Allmon3 requires the following:

* PHP with the PHP-ZMQ package
* Webserver configured to host PHP-based applications (Apache and Nginx supported)
* Python3 with the Python ZMQ package

## Installation
These are *alpha* quality installation instructions. Eventually the plan is this
will be an installable package. At the moment, these are Debian-specific and 
assume you already know how to install a webserver with PHP support.

1. Install dependencies `apt install -y php-zmq python3-zmq`

2. Copy the files into place:
```
cp asl-statmon/asl-statmon /usr/local/bin
cp asl-statmon-test-client.py /usr/local/bin
cp example.ini /usr/local/etc/allmon3.ini
cp asl-statmon@.service /etc/systemd/system
cp -r web /var/www/html/allmon3
```

3. Edit `allmon3.ini` for at least one ASL AMI interface. Each node
must have a separately-numbered `monport=` value. It's recommended
to start with port 6750 and count up from there for each node configured
in the .ini file. Here's an example for monitoring three ASL Nodes:

```
[50815]
ip=172.17.16.36
user=admin
pass=password
monport=6750

[460180]
ip=172.17.16.217
user=admin
pass=password
monport=6751

[48496]
ip=208.167.248.86
user=admin
pass=password
monport=6752
```

4. Start the asl-statmon process(es) for each node. These are done
with a systemd services instance launcher. For each node to be
monitoried - `systemctl start asl-statmon@NNNNN` where NNNNN is 
the node number. For example `systemctl start asl-statmon@50815`.

5. Navigate to the website provided by the server at /allmon3/
and hopefully stuff will Just Work(SM)

## Three-Tier Structure
Allmon3 is organized around a tierd structure: Asterisk AMI, stats monitor (asl-statmon), 
and the website. In order to reduce webserver load see in Allmon2 (especially for systems 
using workers with php-fpm) and on Asterisk AMI calls, one asl-statmon process operates
as a [https://zeromq.org/](0MQ Messaging Publisher) polling AMI one time and distributing
the information to many web clients efficiently. It also allows for interesting things
such as different views and abstractions of clusters of Asterisk servers and it permits
polling of many nodes running on the same Asterisk server to be efficient.

A generalized architecture is as follows:

```
 +---------------+                     +--------------+
 |  Asterisk ASL |                     | asl-statmon  |
 |  Node 1234    | <---- TCP/5038 ---- | Node 1234    | <-            
 |  192.0.2.10   |                     | 203.0.113.20 |   \ TCP/6750  +--------------+ 
 +---------------+                     +--------------+    \          | Webserver    |
                                                           +----------| 203.0.113.20 | --== MANY CLIENTS
 +---------------+                     +--------------+    /          | PHP + ZMQ    |
 |  Asterisk ASL |                     | asl-statmon  |   / TCP/6751  +--------------+
 |  Node 2345    | <---- TCP/5038 ---- | Node 2345    | <-
 |  192.51.100.1 |                     | 203.0.113.20 |
 +---------------+                     +--------------+
```

