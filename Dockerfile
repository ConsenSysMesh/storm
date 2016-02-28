FROM ubuntu:wily
MAINTAINER caktux

ENV DEBIAN_FRONTEND noninteractive

# Usual update / upgrade
RUN apt-get update
RUN apt-get upgrade -q -y
RUN apt-get dist-upgrade -q -y

# Install fetch and versioneer equirements
RUN apt-get install -q -y curl git

# Install requirements
RUN apt-get install -q -y pkg-config python python-dev

ENV DOCKER_ENGINE_VERSION latest
ENV DOCKER_COMPOSE_VERSION 1.6.2
ENV DOCKER_MACHINE_VERSION 0.6.0

# Install docker-machine, docker-compose and docker client
RUN curl -fSL "https://get.docker.com/builds/Linux/x86_64/docker-$DOCKER_ENGINE_VERSION" -o /usr/bin/docker
RUN chmod +x /usr/bin/docker
RUN curl -fSL "https://github.com/docker/compose/releases/download/$DOCKER_COMPOSE_VERSION/docker-compose-Linux-x86_64" -o /usr/bin/docker-compose
RUN chmod +x /usr/bin/docker-compose
RUN curl -fSL "https://github.com/docker/machine/releases/download/v$DOCKER_MACHINE_VERSION/docker-machine-Linux-x86_64" -o /usr/bin/docker-machine
RUN chmod +x /usr/bin/docker-machine

# Install pip
RUN curl -fSL "https://bootstrap.pypa.io/get-pip.py" | python

# We add requirements.txt first to prevent unnecessary local rebuilds
ADD requirements.txt /
RUN pip install -r requirements.txt

# Install storm
ADD . storm
WORKDIR storm
RUN pip install -e .

# Mount ~/.docker/machine to use existing Docker machines
VOLUME ["/root/.docker/machine"]

# Mount your local ~/.storm for credentials and certificates
VOLUME ["/root/.storm"]
