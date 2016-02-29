#!/usr/bin/env python
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
"""
Storm - multi-cloud load-balanced deployments

    TODO Implement "repair" command
    TODO Use contextmanager to send fabric's output to a logger (?)
    TODO Make a futures wrapper for better pattern reuse in tasks
"""
import os
import json
import base64
import uuid
import yaml
import logging
import argcomplete
from colors import colors
from fabric.api import settings
from fabric.contrib.console import confirm
from tasks import set_logging, machine, machine_list, docker_on, compose_on
from tasks import launch, deploy_consul, deploy_registrator, prepare_haproxy, deploy_haproxy
from tasks import stop_machines, teardown, rollback
from tasks import AWS_ACCESS_KEY, AWS_SECRET_KEY, AZURE_SUBSCRIPTION_ID, AZURE_CERTIFICATE, DIGITALOCEAN_ACCESS_TOKEN
from argparse import ArgumentParser
from . import __version__

log = logging.getLogger(__name__)

# Get available scenarios
path = os.path.dirname(__file__)

def parse_arguments(parser):
    parser.add_argument(
        "--debug",
        default=False,
        dest="debug",
        type=bool,
        help="Debug (default: %(default)s)")
    parser.add_argument(
        "command",
        choices=["launch", "deploy", "repair", "env", "ls", "ps", "up", "scale", "stop", "rm", "teardown"],
        help="Storm commands for deployments and maintenance")
    parser.add_argument(
        "parameters",
        nargs='*',
        help="Optional parameters per command")

    argcomplete.autocomplete(parser)

    return parser.parse_args()

class Inventory(object):
    def __init__(self):
        machines = self.parse_machines()

        self.discovery = machines['discovery']
        self.instances = machines['instances']

    def parse_machines(self):
        machines = machine_list().splitlines()[1:]
        parsed = {}
        discovery = {}
        instances = {}

        for mach in machines:
            fields = mach.split()
            ip = fields[4][6:-5]
            if mach.startswith('consul-'):
                discovery.update({fields[0]: ip})
            else:
                instances.update({fields[0]: ip})

        parsed['discovery'] = discovery
        parsed['instances'] = instances

        return parsed

def load_yaml():
    log.debug("Loading storm.yml ...")
    f = open("storm.yml")
    data = yaml.load(f)
    f.close()
    log.debug(json.dumps(data, indent=4))

    return data

def create_certs():
    # Create certs if they don't exist, otherwise we can end up creating
    # the same file in parallel in preparation steps
    if not os.path.exists(os.path.join(os.path.expanduser("~"), ".docker", "machine", "certs")):
        log.info("No certificates found, creating them...\n")
        machine("create -d none --url tcp://127.0.0.1:2376 dummy", threadName="create cert")
        machine("rm -y dummy", threadName="rm")
        log.info("Certificates created.\n")

def main():
    parser = ArgumentParser(version=__version__)
    args = parse_arguments(parser)

    set_logging(args.debug)

    logo = ("   ______     %s%s%s\n"
            "  / __/ /____  ______ _\n"
            " _\ \/ __/ _ \/ __/  ' \\\n"
            "/___/\__/\___/_/ /_/_/_/\n" % (colors.BLUE, __version__, colors.GREEN))

    if args.command != "env":
        log.info('%s=========%s' % (colors.PURPLE, colors.ENDC))
        log.info('%s%s%s' % (colors.GREEN, logo, colors.ENDC))
        log.info('%s========================%s\n' % (colors.PURPLE, colors.ENDC))

    if args.command == "ls":
        # List machines
        machines = machine_list()
        log.info("Machines:")
        log.info(machines)
        log.info("===")
        raise SystemExit

    elif args.command == "stop":
        names = args.parameters
        if not names:
            log.warn("No machine specified.")
        else:
            if not confirm("This will terminate %s, continue?" % names, default=False):
                log.warn("Aborting...")
                raise SystemExit
        stop_machines(names)
        raise SystemExit

    elif args.command == "rm":
        names = args.parameters
        if not names:
            inventory = Inventory()
            for name in inventory.instances:
                names.append(name)
        if not confirm("This will terminate %s, continue?" % names, default=False):
            log.warn("Aborting...")
            raise SystemExit
        teardown(names)
        raise SystemExit

    elif args.command == "teardown":
        # Cleanup - TODO filters
        if not confirm("This will terminate all instances, continue?", default=False):
            log.warn("Aborting...")
            raise SystemExit
        names = []
        inventory = Inventory()
        for name in inventory.instances:
            names.append(name)
        if args.parameters and args.parameters[0] == "all":
            for name in inventory.discovery:
                names.append(name)
        teardown(names)
        raise SystemExit

    elif args.command == "launch":
        # Make sure we have docker-machine certificates
        create_certs()

        if len(args.parameters) < 2:
            log.warn("Please select a provider and unique instance name.")
            raise SystemExit

        provider = args.parameters[0]
        if provider == "azure":
            if AZURE_SUBSCRIPTION_ID and AZURE_CERTIFICATE:
                machine('create -d azure --azure-subscription-id="%s" --azure-subscription-cert="%s" %s' % (AZURE_SUBSCRIPTION_ID,
                                                                                                            AZURE_CERTIFICATE,
                                                                                                            args.parameters[1]),
                        threadName="create %s" % args.parameters[1])
            else:
                log.warn("Missing Azure credentials, set them in ~/.storm/azure/")

        elif provider == "aws":
            if AWS_ACCESS_KEY and AWS_SECRET_KEY:
                machine('create -d amazonec2 --amazonec2-access-key="%s" --amazonec2-secret-key="%s" %s' % (AWS_ACCESS_KEY,
                                                                                                            AWS_SECRET_KEY,
                                                                                                            args.parameters[1]),
                        threadName="create %s" % args.parameters[1])
            else:
                log.warn("Missing AWS credentials, set them as standard credentials in ~/.aws/credentials")

        elif provider == "digitalocean":
            if AWS_ACCESS_KEY and AWS_SECRET_KEY:
                machine('create -d digitalocean --digitalocean-access-token="%s" %s' % (DIGITALOCEAN_ACCESS_TOKEN,
                                                                                        args.parameters[1]),
                        threadName="create %s" % args.parameters[1])
            else:
                log.warn("Missing DigitalOcean token, set it in ~/.storm/digitalocean/token")

        else:
            log.warn("Unknown provider or not implemented yet.")
        raise SystemExit

    elif args.command == "deploy":
        # Make sure we have docker-machine certificates
        create_certs()

        # Load YAML definitions
        storm = load_yaml()

        # Summary and totals
        summary = {
            "hosts": {
                "title": "Instances",
                "total": 0,
                "summary": ""
            },
            "discovery": {
                "title": "Discovery instances",
                "total": 0,
                "summary": ""
            }
        }
        for section in summary:
            for provider in storm[section]:
                options = storm[section][provider]
                provider_details = []
                provider_scale = 0
                if isinstance(options, list):
                    for location in options:
                        provider_scale += location["scale"]
                        summary[section]["total"] += location["scale"]
                        if "size" in location and "location" in location:
                            provider_details.append("%s in %s" % (location["size"], location["location"]))
                        elif "size" in location:
                            provider_details.append("%s" % location["size"])
                        elif "location" in location:
                            provider_details.append("%s" % location["location"])
                        else:
                            provider_details.append("default")
                else:
                    provider_scale += options["scale"]
                    summary[section]["total"] += options["scale"]
                    if "size" in options and "location" in options:
                        provider_details.append("%s in %s" % (options["size"], options["location"]))
                    elif "size" in options:
                        provider_details.append('%s' % options["size"])
                    elif "location" in options:
                        provider_details.append("%s" % options["location"])
                    else:
                        provider_details.append("default")
                summary[section]["summary"] += "  %s: %s (%s)\n" % (provider, provider_scale, ", ".join(provider_details))
            log.info("%s:\n%s" % (summary[section]["title"], summary[section]["summary"]))

        log.info("Totals: %s%d instances%s on %s%d cloud providers%s" % (
                 colors.GREEN, summary["hosts"]["total"], colors.ENDC, colors.BLUE, len(storm["hosts"]), colors.ENDC))
        log.info("      + %s%d discovery instances%s on %s%d cloud providers%s\n" % (
                 colors.PURPLE, summary["discovery"]["total"], colors.ENDC, colors.BLUE, len(storm["discovery"]), colors.ENDC))

        # Confirm setup parameters
        if not confirm("Continue?"):
            log.warn("Aborting...")
            raise SystemExit

        names = []
        instances = {}
        discovery = {}
        inventory = Inventory()
        log.debug("Current inventory: %s, %s" % (inventory.discovery, inventory.instances))

        #
        # Launch discovery instances
        #
        log.info("Launching %sdiscovery%s instances..." % (colors.PURPLE, colors.ENDC))

        # Launch service discovery instances
        for provider in storm["discovery"]:
            if isinstance(storm["discovery"][provider], list):
                for l, location in enumerate(storm["discovery"][provider]):
                    for index in range(location["scale"]):
                        name = "consul-%s-%d-%d-%s" % (provider, l, index, str(uuid.uuid4())[:8])
                        instance = location.copy()
                        instance["provider"] = provider
                        instance["name"] = name
                        discovery[name] = instance
            else:
                for index in range(storm["discovery"][provider]["scale"]):
                    name = "consul-%s-%d-%s" % (provider, index, str(uuid.uuid4())[:8])
                    instance = storm["discovery"][provider].copy()
                    instance["provider"] = provider
                    instance["name"] = name
                    discovery[name] = instance

        if len(discovery) == 1:
            log.warn("%sWARNING%s: Using a single instance for service discovery provides no fault tolerance." % (colors.YELLOW, colors.ENDC))

        if summary["discovery"]["total"] and not inventory.discovery:
            with settings(warn_only=False), rollback(discovery.keys()):
                launch(discovery)

            # Deploy Consul on discovery instances
            inventory = Inventory()
            log.info("Deploying %sConsul%s%s..." % (colors.PURPLE, colors.ENDC, " cluster" if len(inventory.discovery) > 1 else ""))
            encrypt = base64.b64encode(str(uuid.uuid4()).replace('-', '')[:16])
            deploy_consul(inventory.discovery, encrypt)

        # Add discovery instances names to list
        for name in inventory.discovery:
            names.append(name)

        # FIXME Setting discovery as first IP of Consul cluster until DNS setup is implemented
        discovery_host = inventory.discovery[inventory.discovery.keys()[0]]

        #
        # Launch cluster instances
        #
        log.info("Launching %scluster%s instances..." % (colors.BLUE, colors.ENDC))

        for provider in storm["hosts"]:
            if isinstance(storm["hosts"][provider], list):
                for l, location in enumerate(storm["hosts"][provider]):
                    for index in range(location["scale"]):
                        name = "storm-%s-%d-%d-%s" % (provider, l, index, str(uuid.uuid4())[:8])
                        instance = location.copy()
                        instance["discovery"] = discovery_host
                        instance["provider"] = provider
                        instance["name"] = name
                        instances[name] = instance
            else:
                for index in range(storm["hosts"][provider]["scale"]):
                    name = "storm-%s-%d-%s" % (provider, index, str(uuid.uuid4())[:8])
                    instance = storm["hosts"][provider].copy()
                    instance["discovery"] = discovery_host
                    instance["provider"] = provider
                    instance["name"] = name
                    instances[name] = instance

        if summary["hosts"]["total"] and not inventory.instances:
            launch(instances)

            # Reload inventory
            inventory = Inventory()

        log.info("Launched %s%d instances%s, %s%d discovery instances%s" % (
                 colors.GREEN, len(inventory.instances), colors.ENDC,
                 colors.PURPLE, len(inventory.discovery), colors.ENDC))

        # Need a better way to get the swarm master...
        swarm_master = inventory.instances.keys()[0]

        # Deploy and scale registrator to all instances
        log.info("Deploying %sregistrator%s..." % (colors.GREEN, colors.ENDC))
        deploy_registrator(
            swarm_master,
            len(inventory.instances),
            discovery_host)

        # Prepare instances for HAProxy (transfer certificate for HTTPS)
        log.info("Preparing %sHAProxy%s..." % (colors.GREEN, colors.ENDC))
        prepare_haproxy(inventory.instances.keys())

        # Deploy HAProxy
        log.info("Deploying %s%d HAProxy%s instances..." % (colors.GREEN, storm["load_balancers"], colors.ENDC))
        deploy_haproxy(
            swarm_master,
            storm["load_balancers"],
            discovery_host)

        # Add cluster instances names to list
        for name in inventory.instances:
            names.append(name)

        # List inventory
        if args.debug:
            # List machines
            machines = machine_list()
            log.info("Machines:")
            log.info(machines)
            log.info("===")

            log.debug('Discovery: %s' % inventory.discovery)
            log.debug('Instances: %s' % inventory.instances)
            log.debug("Names: %s" % names)

        # Deploy services
        for name in storm["deploy"]:
            services = storm["deploy"][name]["services"]
            for service in services:
                log.info("Deploying %s%s%s..." % (colors.GREEN, service, colors.ENDC))
                config = services[service]
                # with lcd(os.path.join(os.getcwd(), 'deploy', name)):
                compose_on(swarm_master, "up -d", discovery_host,
                           cwd=os.path.join(os.getcwd(), 'deploy', name))
                compose_on(swarm_master, "scale %s=%d" % (service, config["scale"]), discovery_host,
                           cwd=os.path.join(os.getcwd(), 'deploy', name))

        # Teardown?
        if confirm("Teardown running instances?", default=False):
            teardown(names)

    elif args.command == "repair":
        log.warn("Not implemented, yet.")
        raise SystemExit

    elif args.command == "ps":
        inventory = Inventory()
        discovery_host = inventory.discovery[inventory.discovery.keys()[0]]  # FIXME
        master_instance = inventory.instances.keys()[0]  # FIXME too
        out = docker_on(master_instance, "ps " + " ".join(args.parameters), discovery_host, threadName="ps swarm %s" % master_instance, capture=True)
        print out

    elif args.command == "env":
        inventory = Inventory()
        if args.parameters[0] == 'swarm':
            instance = inventory.instances.keys()[0]
            out = machine("env --shell bash --swarm %s" % instance, threadName="env %s" % instance, capture=True)
            print out
        elif args.parameters[0] == 'discovery':
            instance = inventory.discovery.keys()[int(args.parameters[1])]
            out = machine("env --shell bash %s" % instance, threadName="env %s" % instance, capture=True)
            print out
        else:
            instance = inventory.instances.keys()[int(args.parameters[0])]
            out = machine("env --shell bash %s" % instance,
                          threadName="env %s" % instance, capture=True)
            print out

    else:
        if args.command:
            inventory = Inventory()
            discovery_host = inventory.discovery[inventory.discovery.keys()[0]]  # FIXME
            master_instance = inventory.instances.keys()[0]  # FIXME too
            compose_on(master_instance, args.command + " " + " ".join(args.parameters), discovery_host, verbose=True)
        else:
            log.warn("No docker-compose arguments found to process.")

if __name__ == '__main__':
    main()
