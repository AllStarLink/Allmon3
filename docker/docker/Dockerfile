##
## Debian version to compose - Supported options are
## '12-slim' and '13-slim'
ARG DEB_VER="13-slim"

## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
## Without experience, do not change past this line
## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

FROM debian:$DEB_VER
WORKDIR /root

# setup fake systemd environment
COPY ./fake-systemctl /usr/bin/systemctl
RUN chmod +x /usr/bin/systemctl

# build the core
COPY ./allmon3-init.sh /root/allmon3-init.sh
RUN chmod +x /root/allmon3-init.sh
RUN /root/allmon3-init.sh

# Prep the runtime
COPY ./allmon3-web.sh /root/allmon3-web.sh
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 80

CMD ["/usr/bin/supervisord"]
