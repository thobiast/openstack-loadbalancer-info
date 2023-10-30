openstack-lb-info - A script to display OpenStack Load Balancer resource details.


[![Build and Test](https://github.com/thobiast/openstack-loadbalancer-info/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/thobiast/openstack-loadbalancer-info/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


# About

This Python script is designed to interact with an OpenStack cloud infrastructure and retrieve information about
load balancers and their components such as listeners, pools, health monitors, members, and amphorae.
It displays the information in a visually appealing and user-friendly way and provide a clear representation
of the load balancer resources.

Below are the key features and components:

## Features

- Query and display information about OpenStack load balancers.
- Display detailed attributes and information about listeners, pools, health monitors, members, and amphorae.
- Filter results based on various criteria, such as load balancer name, ID, tags, availability zone, VIP network, and VIP subnet.
- Present information in a structured and colorful format using the Rich library.

## Information Display

The program provides two main modes for displaying information:

1. **Load Balancer Information:** When the resource type is specified as "lb," it retrieves and displays
details about OpenStack load balancers. The displayed information includes load balancer IDs, VIP addresses, provisioning status,
operating status, and other optional details. If no load balancers match the filter criteria, it will indicate that
no load balancers were found.

2. **Amphora Information:** When the resource type is specified as "amphora," it retrieves and displays information
about amphoras associated with load balancers. Amphoras are responsible for handling load balancing operations. The displayed
information includes amphora IDs, roles, status, load balancer network IP addresses, associated images, server information,
and optional details. If no amphoras match the filter criteria, it will indicate that no amphoras were found.

## Example

```bash
$ usage: openstack-lb-info [-h] --type {lb,amphora} [--name NAME] [--id ID] [--tags TAGS]
                           [--availability-zone AVAILABILITY_ZONE]
						   [--vip-network-id VIP_NETWORK_ID]
                           [--vip-subnet-id VIP_SUBNET_ID] [--details]

A script to show OpenStack load balancers information.

options:
  -h, --help            show this help message and exit
  --type {lb,amphora}   Show information about load balancers or amphoras
  --name NAME           Filter load balancers name
  --id ID               Filter load balancers id
  --tags TAGS           Filter load balancers tags
  --availability-zone AVAILABILITY_ZONE
                        Filter load balancers AZ
  --vip-network-id VIP_NETWORK_ID
                        Filter load balancers network id
  --vip-subnet-id VIP_SUBNET_ID
                        Filter load balancers subnet id
  --details             Show all load balancers/amphora details

    Example of use:
        openstack-lb-info
        openstack-lb-info --type lb --name my_lb
        openstack-lb-info --type lb --id load_balancer_id
        openstack-lb-info --type amphora --id load_balancer_id
        openstack-lb-info --type amphora --id load_balancer_id --details
```
![example](img/example.png)


## Usage

Clone or download the repository to your local machine.

### Install in development mode using pip
```bash
$ pip install -e .
```

### Install in development mode using pipx
```bash
$ pipx install -e .
```
