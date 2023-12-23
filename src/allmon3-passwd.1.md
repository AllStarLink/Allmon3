% allmon3-passwd(1) allmon3-passwd @-DEVELOP@@
% Jason McCormick
% April 2023

# NAME
allmon3-passwd - Manage the users table for Allmon3

# SYNOPSIS
usage: allmon3-passwd [-h] [\-\-delete] [\-\-debug] [\-\-file FILE] [\-\-version] user

Manage Allmon3 password file

positional arguments:
  user         username to create/modify

optional arguments:
  -h, \-\-help   show this help message and exit

  \-\-delete     delete the user specified by 'user'

  \-\-debug      enable debug-level logging output

  \-\-file FILE  alternate file to edit; default /etc/allmon3/users

  \-\-version    get the version of the software

# DESCRIPTION
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

Deleting a user is simply adding the `\-\-delete` flag to the command:

```
$ allmon3-passwd \-\-delete allmon3
```

# BUGS
Report bugs to https://github.com/AllStarLink/Allmon3/issues

# COPYRIGHT
Copyright (C) 2023 Jason McCormick and AllStarLink
under the terms of the AGPL v3.



