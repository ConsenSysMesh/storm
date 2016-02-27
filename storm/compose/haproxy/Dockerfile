FROM haproxy
MAINTAINER caktux

ENV DEBIAN_FRONTEND noninteractive

# HTTP stats page
EXPOSE 88

EXPOSE 443

RUN deps='curl unzip' && \
    apt-get update && \
    apt-get install -y $deps && \
    curl -L -o /tmp/consul-template.zip https://releases.hashicorp.com/consul-template/0.13.0/consul-template_0.13.0_linux_amd64.zip && \
    cd /tmp && \
    unzip consul-template.zip && \
    cp consul-template /usr/bin/consul-template && \
    chmod a+x /usr/bin/consul-template && \
    apt-get purge -y --auto-remove $deps

ADD haproxy.cfg /etc/haproxy/haproxy.cfg
ADD haproxy.template /etc/haproxy/haproxy.template

ADD start.sh /start.sh
RUN chmod u+x /start.sh
ADD reload.sh /reload.sh
RUN chmod u+x /reload.sh

RUN useradd haproxy -s /sbin/nologin

WORKDIR /

VOLUME ["/etc/ssl/private/certificate.pem"]

CMD ["/start.sh"]
