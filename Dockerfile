FROM ubuntu:wily
MAINTAINER caktux

ENV DEBIAN_FRONTEND noninteractive

# Usual update / upgrade
RUN apt-get update
RUN apt-get upgrade -q -y
RUN apt-get dist-upgrade -q -y

# Install python, curl, and git to display version with versioneer
RUN apt-get install -q -y python git

ENV DOCKER_ENGINE_VERSION latest
ENV DOCKER_COMPOSE_VERSION 1.6.2
ENV DOCKER_MACHINE_VERSION 0.6.0

# Install docker-machine, docker-compose, docker engine and pip
RUN apt-get install -q -y curl && \
    curl -fSL "https://get.docker.com/builds/Linux/x86_64/docker-$DOCKER_ENGINE_VERSION" -o /usr/bin/docker && \
    chmod +x /usr/bin/docker && \
    curl -fSL "https://github.com/docker/compose/releases/download/$DOCKER_COMPOSE_VERSION/docker-compose-Linux-x86_64" -o /usr/bin/docker-compose && \
    chmod +x /usr/bin/docker-compose && \
    curl -fSL "https://github.com/docker/machine/releases/download/v$DOCKER_MACHINE_VERSION/docker-machine-Linux-x86_64" -o /usr/bin/docker-machine && \
    chmod +x /usr/bin/docker-machine && \
    curl -fSL "https://bootstrap.pypa.io/get-pip.py" | python && \
    apt-get purge -y curl && \
    apt-get --purge autoremove -y

# We add requirements.txt first to prevent unnecessary local rebuilds
ADD requirements.txt /
RUN deps="build-essential pkg-config python-dev" && \
    apt-get install -q -y $deps && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y $deps gcc cpp libc6-dev libgcc-5-dev libstdc++-5-dev && \
    apt-get --purge autoremove -y && \
    apt-get clean

# Install bash-completion, activate argcomplete and add bash-completion.d
RUN apt-get install -q -y bash-completion
RUN activate-global-python-argcomplete
RUN echo ". /usr/share/bash-completion/bash_completion" >> ~/.bashrc

# Install vim for in-container edits
# RUN apt-get install -q -y vim

# Install storm
ADD . storm
WORKDIR storm
RUN pip install -e .

# Mount ~/.docker/machine for persistence of Docker machines across container restarts
VOLUME ["/root/.docker/machine"]

# Mount your local ~/.storm for credentials and certificates
VOLUME ["/root/.storm"]
