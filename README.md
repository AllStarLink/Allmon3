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

## :warning: Security Warning :biohazard:
Please note that currently the web frontend application has NOT IMPLEMENTED
any logon security yet. If you deploy this repository as-is with
a functioning `api/asl-cmdlink.php` you should make
other security provisions such as enabling webserver-based HTTP authentication
or adding IP ACLs to the `api/asl-cmdlink.php` function. Alternatively, deleting
`api/asl-cmdlink.php` works and will not impact the rest of the application.


## Installation
These are *alpha* quality installation instructions. Eventually the plan is this
will be an installable package. At the moment, these are Debian-specific and 
assume you already know how to install a webserver with PHP support.

1. Install dependencies `apt install -y php-zmq python3-zmq make rsync`

2. Install the application using make
```
make install
```

This will install everything into `/etc`, `/usr/local/bin`, `/usr/local/etc`,
and `/var/www/html/allmon3`. The `DESTDIR=` modifier is available if you want
to install monolithically into a seaprate location. For example:

```
make install DESTDIR=/path/to/temp/location
```
3. Enable and start the services
```
systemctl daemon-reload
systemctl enable asl-statmon@NODE
systemctl enable asl-cmdlink@NODE
systemctl start asl-statmon@NODE
systemctl start asl-cmdlink@NODE
```

In the above, replace "NODE" with your ASL node ID - for example:

```
systemctl enable asl-statmon@1999
systemctl enable asl-cmdlink@1999
systemctl start asl-statmon@1999
systemctl start asl-cmdlink@1999
```

If you have multiple nodes, you need one each of `asl-statmon@NODE` and `asl-cmdlink@NODE` per node. Multiple nodes on the same syste should use the `multinodes=/colocated_on=` structure described in `allmon3.ini`.

4. Edit `/usr/local/etc/allmon3.ini` for at least one ASL AMI interface. Each node
must have a separately-numbered `monport=` and `cmdport=` value. It's recommended
to start with port 6750 for `monport` and 6850 for `cmdport`
 and count up from there for each node configured in the .ini file. 
Here's an example for monitoring three ASL Nodes:

```
[50815]
ip=172.17.16.36
user=admin
pass=password
monport=6750
cmdport=6850

[460180]
ip=172.17.16.217
user=admin
pass=password
monport=6751
cmdport=6851

[48496]
ip=208.167.248.86
user=admin
pass=password
monport=6752
cmdport=6852
```

Note, that for the web interface a separate, distinct configuration file
can be placed in the webroot under the api folder 
(e.g. `/var/www/html/allmon3/api/allmon3.ini.php`)
which will be used *in place of* the common `/usr/local/etc/allmon3.ini`. No
configuration is need to use a web-local configuration and the .ini format
is identical. Please note that the file in the web directory ends in `.ini.php` as 
a security feature to ensure that the credentials are not exposed to the Internet.

5. Navigate to the website provided by the server at /allmon3/
and hopefully stuff will Just Work(SM)

## Three-Tier Structure
Allmon3 is organized around a tierd structure: Asterisk AMI, stats monitor (asl-statmon), 
and the website. In order to reduce webserver load see in Allmon2 (especially for systems 
using workers with php-fpm) and on Asterisk AMI calls, one asl-statmon process operates
as a [0MQ Messaging Publisher](https://www.zeromq.org/) polling AMI one time and distributing
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

