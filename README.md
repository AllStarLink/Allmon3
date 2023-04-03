# Allmon3

![GitHub](https://img.shields.io/github/license/AllStarLink/Allmon3)

![Bootstrap](https://img.shields.io/badge/bootstrap-%23563D7C.svg?style=for-the-badge&logo=bootstrap&logoColor=white) ![PHP](https://img.shields.io/badge/php-%23777BB4.svg?style=for-the-badge&logo=php&logoColor=white) ![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

Allmon is the standard web-based montitoring and management for the AllStarLink
application. Allmon3 is the next generation of the venerable Allmon2 that is 
rewritten for performance, scalability, and responsiveness.

## Design Goals
Allmon3 features and functionality shall be governed by the following guidelines:

* Use of modern web responsive design for usability on all device form factors and screen sizes
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
These are *beta quality* installation instructions. Eventually the plan is this
will be an installable package. At the moment, these are Debian-specific and 
assume you already know how to install a webserver with PHP support.

1. Install dependencies `apt install -y php-zmq python3-zmq make rsync`

2. Install the application using make
```
make install
```

This will install everything into `/etc`, `/usr/local/bin`, `/usr/local/etc`,
and `/var/www/html/allmon3`. Note that `/var/www/html/allmon3/api/passwords.php` 
and `/var/www/html/allmon3/css/custom.css` **will not** be overwritten. In the
current beta state, make sure to hand-update these two files as needed.

The `DESTDIR=` modifier is available if you want
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
which will be used *in place of* the common `/usr/local/etc/allmon3.ini`
for the website only. No configuration is need to use a web-local configuration 
when the .ini configuration/contents is identical. Please note that the file
in the web directory ends in `.ini.php` as  a security feature to ensure 
that the AMI credentials are not exposed to the Internet.

5. Navigate to the website provided by the server at /allmon3/
and hopefully stuff will Just Work(SM)

## Usernames / Passwords for the Site
Usernames and passwords are stored in the `api/passwords.php` file in
the webroot directory for Allmon3. The default-configured username
and password combination is `user / password`. **You *must* change this**.

Set a password and remove the default user with the following:

1. Change to the API directory - `cd /var/www/html/allmon3/api`

2. `php password-generate.php USERNAME` will prompt you for a username and password. It will
look something like this:

```
$ php password-generate.php N8EI
        Password: supersecretpass
Confirm Password: supersecretpass
Copy the following line into passwords.php including the ending comma!

'N8EI' => '$argon2id$v=19$m=65536,t=4,p=1$TVpxbGpRYzJVekZ3MEYydA$QXfIeHH15UztDsbBa6tzKzFgYxwsDgt7FLx9GPfJ1Q4',

```

3. Copy the line specified into the file `passwords.php` and delete the row labeled `user`. For example,
the stock file looks like this:

```
## DO NOT EDIT ANYTHING BEFORE THIS LINE!!

'user' => '$argon2id$v=19$m=65536,t=4,p=1$bHhmVEI5RzduN0Z4VE9VRA$Y+KPUyBIwC3jumcSzBtVI3vFupmtCt9F4ejPtoYK6uc',

## DO NOT EDIT ANYTHING AFTER THIS LINE!!

```

After making this change you should see something like:

```
## DO NOT EDIT ANYTHING BEFORE THIS LINE!!

'N8EI' => '$argon2id$v=19$m=65536,t=4,p=1$TVpxbGpRYzJVekZ3MEYydA$QXfIeHH15UztDsbBa6tzKzFgYxwsDgt7FLx9GPfJ1Q4',

## DO NOT EDIT ANYTHING AFTER THIS LINE!!
```
Note that the trailing comma is important!!

You can add more than one user to the file by simply adding multiple lines.

## Allmon3 Web Configuration

Allmon3 has two configuration files to consider. The first is `api/config.php`. This
is where the site name and optional logo can be placed. In a future release, these
two items will be moved to an .ini file.

The second is `api/menu.ini` for creating a customized menu structure. See `api/menu.ini.example`
for complete instructions on how to configure a menu. To enable a menu, simply
rename `menu.ini.example` to `menu.ini` and edit to taste.

Certain colors are able to be modified by editing `css/custom.css`. See the internal comments
for directions.

## Important Web Log Performance Consideration

As a "modern" web application, Allmon3 makes *extensive* use of AJAX callbacks
to the webserver. Depending on your configuration this could results in dozens
or hundreds of log entries per second in the Apache or NGINX access logs. For 
a standard PC-type system (normal hard drive or a virtual machine/VPS), this is not 
a problem. However, as many people install ASL and Allmon on a Raspberry Pi with
an SD Card, this behavior can quickly wear out the card! In these situations, suppressing
access logging from the `api/asl-statmon.php` URI is essential.

For Apache you can take the following steps:

1. For every configuration location of `AccessLog` or `CustomLog` append
the statement `env=!nolog`.

2. Add a single configuration of `SetEnvIf Request_URI "api/asl-statmon.php" nolog`

For example, in a standard vhost-style configuration:

```
CustomLog ${APACHE_LOG_DIR}/access.log combined env=!nolog
SetEnvIf Request_URI "api/asl-statmon.php" nolog
```

## Three-Tier Structure
Allmon3 is organized around a tierd structure: Asterisk AMI, message poller daemons (asl-statmon
and asl-cmdlink), and the web client. In order to reduce webserver and Asterisk AMI load experience
in Allmon2 (especially for systems using workers with php-fpm) and on Asterisk AMI calls, 
one asl-statmon and asl-cmdlink process oprates against each Asterisk AMI port as a 
[0MQ Messaging Publisher](https://www.zeromq.org/) messaging bus. This results in 
polling AMI one time per cycle and distributing the information to many web clients 
efficiently. It also allows for interesting things such as different views and abstractions 
of clusters of Asterisk servers and it permits polling of many nodes running on the same
Asterisk server to be efficient. This structure results in load reductions against busy
nodes of up to 91% in real-world testing.

A generalized architecture is as follows:

![Allmon3 Diagram](https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/.github/Allmon3%20Tier.jpg)
