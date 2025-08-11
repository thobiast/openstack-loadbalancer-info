#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A Python script to display OpenStack Load Balancer details.

This script query an OpenStack environment to present detailed information
about load balancers, including their components such as listeners, pools,
health monitors, members, and amphorae. It connects to an OpenStack
environment using the OpenStack SDK and presents the information in a
structured and user-friendly format. The script supports multiple output
formats, including plain text, and JSON, Rich text (with colors and styling),
allowing for a comprehensive view of the load balancing resources.

Example of use:

    - To display information about load balancer:
    $ openstack-lb-info --type lb --id load_balancer_id
    $ openstack-lb-info --type lb --name load_balancer_name

    - To display information about amphorae associated with load balancers:
    $ openstack-lb-info --type amphora --id load_balancer_id

    - To display detailed information for load balancer resources:
    $ openstack-lb-info --type lb --id load_balancer_id --details

    - To display detailed information about amphorae associated with load balancer:
    $ openstack-lb-info --type amphora --id load_balancer_id --details

For additional usage and options, please refer to the script's command-line help:
$ openstack-lb-info --help
"""

import argparse
import ipaddress
import sys
import uuid

from .formatters import (
    RICH_AVAILABLE,
    JSONOutputFormatter,
    PlainOutputFormatter,
    RichOutputFormatter,
)
from .loadbalancer_info import AmphoraInfo, LoadBalancerInfo
from .openstack_api import OpenStackAPI


###########################################################################
# Parses the command line arguments
###########################################################################
def parse_parameters():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: An object containing the parsed command-line arguments.
    """
    epilog = """
    Example of use:
        %(prog)s
        %(prog)s --type lb --name my_lb
        %(prog)s --type lb --id load_balancer_id
        %(prog)s --type amphora --id load_balancer_id
        %(prog)s --type amphora --id load_balancer_id --details
    """
    parser = argparse.ArgumentParser(
        description="A script to show OpenStack load balancers information.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )

    parser.add_argument(
        "-o",
        "--output-format",
        help="Output format: 'plain', 'rich' or 'json'",
        choices=("plain", "rich", "json"),
        default="rich",
        required=False,
    )
    parser.add_argument(
        "-t",
        "--type",
        help="Show information about load balancers or amphoras",
        choices=("lb", "amphora"),
        required=True,
    )
    parser.add_argument("--name", help="Filter load balancers name", type=str, required=False)
    parser.add_argument("--id", help="Filter load balancers id", type=str, required=False)
    parser.add_argument("--tags", help="Filter load balancers tags", type=str, required=False)
    parser.add_argument(
        "--flavor-id", help="Filter load balancers flavor id", type=str, required=False
    )
    parser.add_argument(
        "--vip-address",
        help="Filter load balancers VIP address",
        type=str,
        required=False,
    )
    parser.add_argument(
        "--availability-zone", help="Filter load balancers AZ", type=str, required=False
    )
    parser.add_argument(
        "--vip-network-id",
        help="Filter load balancers network id",
        type=str,
        required=False,
    )
    parser.add_argument(
        "--vip-subnet-id",
        help="Filter load balancers subnet id",
        type=str,
        required=False,
    )
    parser.add_argument(
        "--details",
        help="Show all load balancers/amphora details",
        action="store_true",
        required=False,
    )

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    validate_arguments(args)

    return args


def validate_arguments(args):
    """
    Validate command-line arguments.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.

    Raises:
        SystemExit: If any validation fails, the script exits.
    """
    # Validate UUIDs parameters
    uuid_args = ["id", "vip_network_id", "vip_subnet_id", "flavor_id"]
    for arg_name in uuid_args:
        arg_value = getattr(args, arg_name)
        if arg_value and not is_valid_uuid(arg_value):
            sys.exit(f"Error: Invalid {arg_name.replace('_', '-')} format. Expected a UUID.")

    # Validate IP address
    if args.vip_address and not is_valid_ip_address(args.vip_address):
        sys.exit("Error: Invalid VIP address format. Expected a valid IP address.")


def is_valid_uuid(uuid_str):
    """
    Check if uuid_str parameter is a valid UUID.

    Args:
        uuid_str (str): The value to check.

    Returns:
        bool: True if valid UUID, False otherwise.
    """
    try:
        uuid.UUID(str(uuid_str))
        return True
    except ValueError:
        return False


def is_valid_ip_address(address):
    """
    Check if the address parameter is a valid IP address.

    Args:
        address (str): The IP address to validate.

    Returns:
        bool: True if valid IP address, False otherwise.
    """
    try:
        ipaddress.ip_address(address)
        return True
    except ValueError:
        return False


def query_openstack_lbs(openstackapi, args, formatter):
    """
    Query OpenStack Load Balancers based on user-defined filters.

    Args:
        openstackapi (OpenStackAPI): An instance of OpenStackAPI.
        args (argparse.Namespace): Parsed command-line arguments.
        formatter (OutputFormatter): Formatter instance.

    Returns:
        list: A list of OpenStack Load Balancer objects that match the specified
            filters, or an empty list if no load balancers match the criteria.
    """
    # Define filter criteria. It includes only keys with non-None values.
    filter_criteria = {
        k: v
        for k, v in {
            "tags": args.tags,
            "availability_zone": args.availability_zone,
            "vip_network_id": args.vip_network_id,
            "vip_subnet_id": args.vip_subnet_id,
            "flavor_id": args.flavor_id,
            "vip_address": args.vip_address,
            "id": args.id if args.id else None,
        }.items()
        if v is not None
    }

    with formatter.status("Querying load balancers..."):
        filtered_lbs_tmp = openstackapi.retrieve_load_balancers(filter_criteria)

    # Perform name filtering here rather than adding it to filter_criteria
    # because this allows for partial matching of the lb name
    if args.name:
        filtered_lbs = [lb for lb in filtered_lbs_tmp if args.name in lb.name]
    else:
        filtered_lbs = list(filtered_lbs_tmp)

    return filtered_lbs


def get_formatter(output_format):
    """
    Initialize and return the appropriate formatter.

    Args:
        output_format (str): The desired output format ('rich', 'plain', 'json').

    Returns:
        OutputFormatter: An instance of the appropriate formatter class.
    """
    formatter_classes = {
        "rich": RichOutputFormatter,
        "plain": PlainOutputFormatter,
        "json": JSONOutputFormatter,
    }
    try:
        return formatter_classes[output_format]()
    except KeyError:
        sys.exit(f"Error: Unknown output format '{output_format}'")


##############################################################################
# Main
##############################################################################
def main():
    """
    Main function to execute script.
    """

    args = parse_parameters()

    if args.output_format == "rich" and not RICH_AVAILABLE:
        sys.exit(
            "Error: 'rich' library is not installed. "
            "Please install it or choose another output format."
        )

    # Initialize the formatter
    formatter = get_formatter(args.output_format)

    # Create an instance of OpenStackAPI
    openstackapi = OpenStackAPI()

    filtered_lbs = query_openstack_lbs(openstackapi, args, formatter)

    if not filtered_lbs:
        formatter.print("No load balancer(s) found.")
        sys.exit(1)

    for lb in filtered_lbs:
        if args.type == "amphora":
            amphora_info = AmphoraInfo(openstackapi, lb, args.details, formatter)
            amphora_info.display_amp_info()
        else:
            lb_info = LoadBalancerInfo(openstackapi, lb, args.details, formatter)
            lb_info.display_lb_info()


##############################################################################
# Run from command line
##############################################################################
if __name__ == "__main__":
    main()

# vim: ts=4
