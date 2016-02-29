docker-storm
============
[![Build Status](https://travis-ci.org/ConsenSys/storm.svg?branch=master)](https://travis-ci.org/ConsenSys/storm) [![PyPI](https://img.shields.io/pypi/v/docker-storm.svg)](https://pypi.python.org/pypi/docker-storm) [![](https://badge.imagelayers.io/caktux/storm:alpine.svg)](https://imagelayers.io/?images=caktux/storm:latest,caktux/storm:alpine 'Get your own badge on imagelayers.io')

Multi-cloud load-balanced deployments.

[![asciicast](https://asciinema.org/a/4rn6431m27q8l8vkr1dbox80x.png)](https://asciinema.org/a/4rn6431m27q8l8vkr1dbox80x)

### Installation

#### With `pip`
```
pip install docker-storm
```

#### With Docker

##### Using images from Docker Hub
Alpine-based (~50 MB download / ~170 MB virtual size):
```
docker pull caktux/storm:alpine
```

Ubuntu-based (~155 MB download / ~400 MB virtual size):
```
docker pull caktux/storm
```

##### Building with `docker-compose`
```
git clone https://github.com/ConsenSys/storm.git
cd storm
docker-compose build
```

#### Bare-metal install
```
sudo apt-get install build-essential pkg-config python python-dev
git clone https://github.com/ConsenSys/storm.git
cd storm
virtualenv venv  # optional
source venv/bin/activate  # optional
pip install .
```
You will also need the latest releases of [docker-machine](https://docs.docker.com/machine/), [docker-compose](https://docs.docker.com/compose/install/) and [docker](https://docs.docker.com/installation/ubuntulinux/).

### Configuration
#### Credentials
Create and add your credentials in the `~/.storm` folder with proper permissions.

##### AWS
Standard credentials in `~/.storm/aws/credentials`
```
[Credentials]
aws_access_key_id = <ACCESS_KEY_ID>
aws_secret_access_key = <SECRET_ACCESS_KEY>
```

##### Azure
Add your subscription ID in `~/.storm/azure/subscription-id`
```
mkdir -p ~/.storm/azure
echo "YOUR_SUBSCRIPTION_ID" > ~/.storm/azure/subscription-id
```
And your certificate as `~/.storm/azure/certificate.pem`

##### DigitalOcean
Add your token in `~/.storm/digitalocean/token`
```
mkdir -p ~/.storm/digitalocean
echo "YOUR_TOKEN" > ~/.storm/digitalocean/token
```

#### Networking
`docker-machine` opens the ports it needs to function, but more ports are needed for the overlay networks and the services you will deploy.

`docker-storm` will also open the following ports for overlay networks and Consul to function properly:

| Protocol | Port                           | Description        |
| -------- | ------------------------------ | ------------------ |
| udp      | 4789                           | Data plane (VXLAN) |
| tcp/udp  | 7946                           | Control plane      |
| tcp      | 8300, 8301+udp, 8302+udp, 8500 | Consul             |

Until automated port opening is implemented for deployed services, a few other default ports get opened (`80`, `443`, `8545`) and you'll have to open custom services' ports manually.

#### Certificate for HTTPS
Add your SSL/TLS certificate for HAProxy in `~/.storm/certificate.pem`

### Running with Docker

##### Using `docker-compose`
```
docker-compose run storm
```

##### Using `docker`
```
docker build -t storm .
docker run -v ~/.storm:/root/.storm -it storm
```

### Usage
```
$ docker-storm --help
usage: docker-storm [-h] [-v] [--debug DEBUG]
                    [{launch,deploy,repair,env,ls,ps,up,scale,stop,rm,teardown}]
                    [parameters [parameters ...]]

positional arguments:
  {launch,deploy,repair,env,ls,ps,up,scale,stop,rm,teardown}
                        Storm commands for deployments and maintenance
  parameters            Optional parameters per command

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  --debug DEBUG         Debug (default: False)
```

#### Deployments

- Create a `storm.yml` file
- Create a `deploy` folder, with your services in sub-folders along with their `docker-compose.yml` file:

        ./
        storm.yml
        deploy/
            hello/
                docker-compose.yml
            redis/
                docker-compose.yml
            ...

- Run `docker-storm deploy`

Example `storm.yml`:
```
hostname: storm.consensys.net
load_balancers: 2

discovery:
  azure:
    scale: 1
    size: Small
  aws:
    scale: 1
    size: t2.micro
    vpc: vpc-c2cb97a7
  digitalocean:
    scale: 1
    size: 512mb

hosts:
  azure:
    -
      scale: 1
      size: Small
      location: West Europe
    -
      scale: 1
      size: Small
      location: East US
  aws:
    scale: 3
    size: t2.small
    vpc: vpc-c2cb97a7
  digitalocean:
    scale: 3
    size: 1gb

deploy:
  hello:
    services:
      app:
        scale: 5
  geth:
    services:
      geth:
        scale: 5
```

#### Repairing cluster
**Not implemented yet**

This command will compare currently running instances with your `storm.yml` definitions, launch missing instances and containers, and repair the state of your cluster.
```
docker-storm repair
```

#### Quick instance launch
```
docker-storm launch aws quick-instance-name
```

#### Environment shortcuts
Just like with `docker-machine`, you can set your Docker environment variables but much more easily, using the index of launched instances instead of their full names.

For single instances:
```
eval $(docker-storm env 0)
```
With swarm flag:
```
eval $(docker-storm env swarm)
```
For discovery instances:
```
eval $(docker-storm env discovery 0)
```

#### `ps` shortcut for Swarm
```
docker-storm ps [-- -a]
```

#### `ls` shortcut
This is really just an alias for `docker-machine ls --filter label=com.storm.managed=true` which filters for machines managed by `docker-storm`.
```
docker-storm ls
```

#### Cleanup

##### Stopping machines
```
docker-storm stop <machine> [<machines>, ...]
```

##### Removing instances
```
docker-storm rm [instance]
```

##### Removing all instances
Add `all` to also remove discovery instances.
```
docker-storm teardown [all]
```
