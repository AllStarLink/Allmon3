# Allmon3

![GitHub](https://img.shields.io/github/license/AllStarLink/Allmon3)

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![Bootstrap](https://img.shields.io/badge/bootstrap-%23563D7C.svg?style=for-the-badge&logo=bootstrap&logoColor=white)

Allmon is the standard web-based monitoring and management for the AllStarLink
application. Allmon3 is the next generation of the venerable Allmon2 that is 
rewritten for performance, scalability, and responsiveness.

## Design Goals
Allmon3 features and functionality shall be governed by the following guidelines:

* Use of modern web responsive design for usability on all device form factors and screen sizes
* Clear separation between long-running tasks and client-based display updates
* Permit reduced workload on potentially slow repeater site links by cleanly supporting the ability to run only the pollers on the device controlling the repeater and run the dashboard in the cloud; easy prevention of unnecessary web traffic, spidering, etc.
* Prioritization of the common use cases of AllStarLink for feature enhancements

## Community
All code of Allmon3 not otherwise licensed (e.g., Bootstrap, etc.) is licensed
under the [GNU Affero General Public License v3](https://www.gnu.org/licenses/why-affero-gpl.html).
The choice of the AGPLv3 promotes giving back to the amateur radio and
ASL communities.

## Quickstart

Note: This software is currently only supported on Debian 11 with the
`bullseye-backports` enabled. Debian 10 support will be added in the near
future.

### Install on Debian 11 / Raspian 11 Software

1. Enable the Debian 11 `bullseye-backports` package repositorty:

```
echo "deb http://deb.debian.org/debian bullseye-backports main" > /etc/apt/sources.list.d/bullseye-backports.list
apt update
```

2. Install the dependencies
```
apt install -y apache2
apt install -y -t bullseye-backports python3-websockets python3-aiohttp python3-aiohttp-session
```

3. Install Allmon3
```
wget https://github.com/AllStarLink/Allmon3/releases/download/
dpkg -i allmon3_
```

### Install Debian 10 / Raspian 10 Software

Note: The version of Python available on Debian 10 is old and does not support
reasonably-modern conventions of the core Pythong Asynchronous I/O subsystem that
is heavily used throughout Allmon3. Notably some of the error-handling features
are not available and you may get strange error messages in your syslog. This issue
cannot be fixed.

1. Enable the Debian 10 `buster-backports` package repository:

```
echo "deb https://deb.debian.org/debian buster-backports main" > /etc/apt/sources.list.d/buster-backports.list
apt update
```

2. Install the DEB/APT-support dependendencies
```
apt install -y apache2
apt install -y -t buster-backports python3-async-timeout python3-attr python3-multidict python3-yarl
```

3. Install Python modules using PIP3
```
apt remove python3-aiohttp python3-websockets
pip3 install aiohttp
pip3 install websockets
```

4. Install Allmon3
```
wget https://github.com/AllStarLink/Allmon3/releases/download/
dpkg -i allmon3_
```

### Configure Allmon

1. Edit `/etc/allmon3/allmon3.ini` for the basic node configuration as explained in the file.

2. Edit `/etc/allmon3/web.ini` as desired.

3. Configure Apache using the following commands:
```
a2enmod proxy_http proxy_wstunnel rewrite
cp /etc/allmon3/apache.conf /etc/apache2/conf-available/allmon3.conf
a2enconf allmon3
systemctl restart apache2
```

If you would prefer to configure Apache differently or have other existing configuration
such as NamedVirtualHosts, use the configuration found in 
`/etc/apache2/conf-available/allmon3.conf` to build a working configuration.

3. Enable and start the services
```
systemctl enable allmon3 
systemctl start allmon3

```
4. Set a password for the default user allmon3:
```
allmon3-passwd allmon3
```

5. Open your web browser to the IP or hostname - for example: http://192.0.2.10/allmon3/

# Configuration

## Node and Daemon Configuration
The stock configuration files are always available at `/usr/share/doc/allmon3/`
for recovery and documentation.

Edit `/etc/allmon3/allmon3.ini` for at least one ASL AMI interface.

Here's an example for monitoring three ASL Nodes:
```
[50815]
host=172.17.16.36
user=admin
pass=password

[460180]
host=172.17.16.217
user=admin
pass=password

[48496]
host=208.167.248.86
user=admin
pass=password
voter=y
votertitle=Megavoter
```

After changing `allmon3.ini` the service `allmon3` must be restarted - `systemctl restart allmon3`.

## Usernames / Passwords for the Site
Usernames and passwords are stored in `/etc/allmon3/users`.
The default-configured username and password combination is `allmon3 / password`. 
**You *must* change this**.

Allmon3's user database is managed by `allmon3-passwd`. Adding a new user
or editing an existing user is the same command. If the user does not exist,
it will be added. If the user does exist, the password will be updated. 
To add or edit a user's password:
```
$ allmon3-passwd allmon3
Enter the password for allmon3: password
Confirm the password for allmon3: password
$
```

That's all there is to it. The `/etc/allmon3/users` file is readable to see that the
Argon2 hash changed for the user.

Deleting a user is simply adding the `--delete` flag to the command:

```
$ allmon3-passwd --delete allmon3
```

After changing a user password, the allmon3 damon must be reloaded
with `systemctl reload allmon3`.

## Server Customization

Allmon3 has multiple configuration files to consider:

* `/etc/allmon3/web.ini` - Has three configuration sections - *web*, 
*syscmds*, and *node-overrides*. The *web* section has the basic
customizations for the Allmon3 site. The *syscmds* section defines
the templates in the "system commands" menu. Add or remove as
desired. The token `@` will be expanded into the selected node 
on which to execute the command. The *node-overrides* section
can be used to override information from the ASL database.

* `/etc/allmon3/custom.css` - Certain CSS customizations to change
colors in the application.

* `/etc/allmon3/menu.ini` - Allows for the customization of the
Allmon3 web menu. By default, the menu is a list of all nodes
found in `allmon3.ini`. Cutomized menus can be configured
as described in `menu.ini.example`.

# Install From Source

This method is **NOT** recommended.
`
1. Install the necessary dependencies using apt, pip, etc.

   Python3 websockets > 11.0 
   Python3 aiohttp > 3.7 and dependencies (yarl, attr, chardet, multidict) 

2. Install the application using make

If this is the first installation of Allmon3 on a fresh system,
the software can be installed simply using `make install`:

```
make install
```

However if this is an upgrade of an existing installation,
add `instconf=n` to the command to prevent your configurations
in `/etc/allmon3` from being overwritten.

```
make install instconf=n
```

This will install everything into `/usr`, `/etc`, and `/lib`. 
The applications will install in `/usr/bin`.
Configuration will be stored in `/etc/allmon3`.
The web files will be in `/usr/share/allmon3` while examples and
other (future) documentation will be in `/usr/share/doc/allmon3`.
Systemd service files will be installed in `/lib/systemd/system`.

Installation is relocatable using the following make(1) parameters:

* `prefix=` will alter the core prefix of `/usr` files and is most
commonly used to install into `/usr/local`. This is recommended
when you care about distro/FHS/packaging fidelity. This relocates
items installed `/usr/bin` and `/usr/share` to, for example,
`/usr/local/bin` and `/usr/local/share`.

* `sysconfdir=` will alter the location of the configuration files to 
`$sysconfdir/allmon3`.

* `sysd_service=` will alter the location of the systemd service files.
The only practical alternative to `/lib/systemd/system` is `/etc/systemd/system`.

* `datadir=` will relocate the web application portion of Allmon3
to `$datadir/allmon3`.

* `docdir=` will relocate the documentation and examples to `$docdir/allmon3`.

For example:
```
make install prefix=/usr/local sysconfdir=/usr/local/etc datadir=/var/www/html sysd_service=/etc/systemd/system
```

All the above variables are also modified further by the `destdir=` variable
which will install the complete system in an alternative location. This is
only really useful for testing in development.

For example:
```
make install destdir=/path/to/temp/location
```

3. Create the necessary `custom.css`:
```
cd /usr/share/allmon3/css && ln -s /etc/allmon3/custom.css
```

After this, follow the configuration steps above.

