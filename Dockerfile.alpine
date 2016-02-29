FROM alpine:edge
MAINTAINER caktux

ENV DOCKER_MACHINE_VERSION 0.6.0
ENV DOCKER_ENGINE_VERSION latest

RUN apk add --no-cache python

RUN apk add --no-cache --virtual .fetch-deps curl && \
    curl -fSL "https://github.com/docker/machine/releases/download/v$DOCKER_MACHINE_VERSION/docker-machine-Linux-x86_64" -o /usr/bin/docker-machine && \
    chmod +x /usr/bin/docker-machine && \
    curl -fSL "https://get.docker.com/builds/Linux/x86_64/docker-$DOCKER_ENGINE_VERSION" -o /usr/bin/docker && \
    chmod +x /usr/bin/docker && \
    curl -fSL "https://bootstrap.pypa.io/get-pip.py" | python && \
    apk del .fetch-deps

RUN pip install --no-cache-dir docker-compose

# We add requirements.txt first to prevent unnecessary local rebuilds
ADD requirements.txt /
RUN apk add --no-cache --virtual .build-deps make gcc musl-dev python-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del .build-deps

# We need git for our pretty versioneer versions, nicer bash, and openssh-client for scp
RUN apk add --no-cache --virtual .run-deps git bash bash-completion docker-bash-completion openssh-client
RUN activate-global-python-argcomplete --dest=- > /usr/share/bash-completion/completions/python-argcomplete
RUN echo -e "PS1='\\u@\\h:\\w\\$ '\n\
bind '\";5C\":forward-word'\n\
bind '\";5D\":backward-word'\n\
. /usr/share/bash-completion/bash_completion" > /root/.bashrc

# Install storm
ADD . storm
WORKDIR storm
RUN pip install --no-cache-dir -e .

# Mount ~/.docker/machine to use existing Docker machines
VOLUME ["/root/.docker/machine"]

# Mount your local ~/.storm for credentials and certificates
VOLUME ["/root/.storm"]

CMD ["/bin/bash"]
