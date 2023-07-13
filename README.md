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

Allmon3 is only supported on Debian 10, Debian 11, and Debian 12 (or the 
Raspbian/Raspberry Pi OS equivalent - e.g. "Raspbian 11"). Note that
these directions will change with the 1.0 release when all packages
are properly available through the ASL Debian repository.

### Install on Debian 12
1. Install dependencies:
```
apt install -y apache2 python3-websockets python3-argon2 python3-aiohttp python3-aiohttp-session
```
2. Install Allmon3
```
wget https://github.com/AllStarLink/Allmon3/releases/download/rel_t_0_11_3/allmon3_0.11.3-1_all.deb
dpkg -i allmon3_0.11.3-1_all.deb
```

### Install on Debian 11 / Raspian 11 Software

1. Enable the Debian 11 `bullseye-backports` package repositorty:

```
echo "deb http://deb.debian.org/debian bullseye-backports main" > /etc/apt/sources.list.d/bullseye-backports.list
apt update
```

2. Install the dependencies
```
apt install -y apache2 python3-argon2 
apt install -y -t bullseye-backports python3-websockets python3-aiohttp python3-aiohttp-session
```

3. Install Allmon3
```
wget https://github.com/AllStarLink/Allmon3/releases/download/rel_t_0_11_3/allmon3_0.11.3-1_all.deb
dpkg -i allmon3_0.11.3-1_all.deb
```

### Install Debian 10 / Raspian 10 Software

1. Enable the Debian 10 `buster-backports` package repository:

```
echo "deb https://deb.debian.org/debian buster-backports main" > /etc/apt/sources.list.d/buster-backports.list
apt update
```

2. Install the dependendencies
```
apt install -y apache2 python3-argon2 
apt install -y -t buster-backports python3-async-timeout python3-attr python3-multidict python3-yarl
```

3. Install Python modules using PIP3
```
apt remove python3-aiohttp python3-websockets
pip3 install aiohttp
pip3 install aiohttp_session
pip3 install websockets
```

4. Install Allmon3 (debian10 version)
```
wget https://github.com/AllStarLink/Allmon3/releases/download/rel_t_0_11_3/allmon3_0.11.3-1_deb10.deb
dpkg -i allmon3_0.11.3-1_deb10.deb
```

### Configure Allmon

1. Edit `/etc/allmon3/allmon3.ini` for the basic node configuration as explained in the file.

2. Edit `/etc/allmon3/web.ini` as desired.

3. Set a password for the default user allmon3:
```
allmon3-passwd allmon3
```

4. Enable and restart the services
```
systemctl enable allmon3 
systemctl restart allmon3

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

* `/etc/allmon3/web.ini` - Has four configuration sections - *web*, 
*syscmds*, *node-overrides*, and *voter-titles*. The *web* section has the basic
customizations for the Allmon3 site. The *syscmds* section defines
the templates in the "system commands" menu. Add or remove as
desired. The token `@` will be expanded into the selected node 
on which to execute the command. The *node-overrides* section
can be used to override information from the ASL database. The *voter-titles*
section is used to set display names for voters.

* `/etc/allmon3/custom.css` - Certain CSS customizations to change
colors in the application. Follows standard CSS rules and syntax.

* `/etc/allmon3/menu.ini` - Allows for the customization of the
Allmon3 web menu. By default, the menu is a list of all nodes
found in `allmon3.ini`. Cutomized menus can be configured
as described in `menu.ini.example`.

# Install From Source

Installation from source no longer supported in the general use case.
