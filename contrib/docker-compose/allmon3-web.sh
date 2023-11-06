#!/bin/bash

sed -ri \
  -e 's!^(\s*CustomLog)\s+\S+!\1 /proc/self/fd/1!g' \
  -e 's!^(\s*ErrorLog)\s+\S+!\1 /proc/self/fd/2!g' \
  -e 's!^(\s*TransferLog)\s+\S+!\1 /proc/self/fd/1!g' \
  "/etc/apache2/conf-enabled/other-vhosts-access-log.conf" \
  "/etc/apache2/sites-enabled/000-default.conf"

apachectl -D FOREGROUND
