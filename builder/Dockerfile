ARG ARCH
ARG OS

FROM $ARCH/debian:$OS

ARG ARCH
ARG OS
ARG ASL_REPO
ARG USER_ID
ARG GROUP_ID

RUN addgroup --gid $GROUP_ID user; exit 0
RUN adduser --disabled-password --gecos '' --uid $USER_ID --gid $GROUP_ID user; exit 0

# Install build dependencies
RUN apt-get update && apt-get -y install \
    build-essential \
    devscripts \
    fakeroot \
    debhelper \
    automake \
    autotools-dev \
    pkg-config \
    git \
    ca-certificates \
    wget \
    --no-install-recommends

# add the allstarlink repo for build deps
RUN echo "deb https://apt.allstarlink.org/repos/$ASL_REPO $OS main" > /etc/apt/sources.list.d/allstarlink.list
RUN wget -O - https://apt.allstarlink.org/repos/repo_signing.gpg | apt-key add -

# Install application dependencies
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y install \
    debhelper quilt zlib1g-dev libgsm1-dev libssl-dev libtonezone-dev libasound2-dev libpq-dev unixodbc-dev libpri-dev libvpb-dev asl-dahdi-source autotools-dev libnewt-dev libspeex-dev libspeexdsp-dev graphviz libcurl4-openssl-dev doxygen gsfonts libpopt-dev libiksemel-dev freetds-dev libvorbis-dev libsnmp-dev libcap-dev libi2c-dev libjansson-dev libusb-dev\
    --no-install-recommends

# Install libreadline dependency - transition to libeditreadline-dev for bullseye
RUN apt-get -y install libreadline-gplv2-dev || apt-get -y install libeditreadline-dev

# Import entrypoint script
COPY ./entrypoint.sh /entrypoint.sh

# Make Executable
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
