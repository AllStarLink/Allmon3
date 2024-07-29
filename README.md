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

Allmon3 is only supported on Debian 12 (or the Raspbian/Raspberry Pi OS
equivalent - e.g. "Raspbian 12").

Support for Debian 10 and Debian 11 ended with the release of AllStarLink v3
and Allmon3 v1.3.0. The last supported version is 1.2.1 which can be
observed at [branch 1.2.1](https://github.com/AllStarLink/Allmon3/tree/rel_1_2_1).

### Install 
1. If not running an a system already running AlLStarLink software, install
the ASL software repository:

```bash
cd /tmp
wget https://repo.allstarlink.org/public/asl-apt-repos.deb12_all.deb
sudo dpkg -i asl-apt-repos.deb12_all.deb
sudo apt update
```

2. Install allmon3:

```bash
apt install allmon3
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

## Per-Node Restrictions for Users
Allmon3 implements a lightweight access control system to restrict commands
from certain users to certain nodes. Restrictions are configured in
`/etc/allmon3/user-restrictions`. Given that the average use case is
all users have similar access, the access control is implemented in
a named-restrictions model for least configuration complexity.

The logic is as follows when checking the restricted access list:

1. If the user is not listed in `user-restrictions` at all
than the user is permitted commands on all configured nodes.

2. If the user is listed in `user-restrictions` and is listed
as restricted to the node being commanded, the user is permitted
to issue the command.

3. If the user is listed in `user-restrictions` but the node
is not listed for that user, the user is prohibited from
issuing the command.

The format of the `user-restrictions` file is:

```
user1 | NODE[,NODE,NODE...]
user2 | NODE

```
Lines beginning with # are comments.

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

# Using Nginx instead of Apache
Nginx can be used instead of Apache. Instead of using the `apache2`
package, install `nginx` using the above directions. After configuring
nginx, edit `/etc/nginx/sites-available/default` (or your preferred site
configuration) and add an `include` directive within the appropriate
`server { }` configuration block. For example:

```
server {
    listen 80 default_server;

    [... other stuff ...]

    include /etc/allmon3/nginx.conf;

    [... other stuff ...]
}
```

# Install From Source

Installation from source no longer supported in the general use case.
However, in general, `make install` should yield a working system.

