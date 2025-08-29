#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A Python script to display OpenStack Load Balancer details.

This script queries an OpenStack environment to present detailed information
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
import logging
import sys
import uuid

from .formatters import (
    RICH_AVAILABLE,
    JSONOutputFormatter,
    PlainOutputFormatter,
    RichOutputFormatter,
)
from .loadbalancer_info import AmphoraInfo, LoadBalancerInfo, ProcessingContext
from .openstack_api import OpenStackAPI

log = logging.getLogger(__name__)

# Max allowed threads for --max-workers
MAX_WORKERS_LIMIT = 32


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
        "-d",
        "--debug",
        help="Enable debug log messages. (default: %(default)s)",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "--os-cloud",
        help=(
            "Name of the cloud to load from clouds.yaml. "
            "(Default '%(default)s', which uses OS_* env vars)"
        ),
        type=str,
        default="envvars",
        required=False,
    )
    parser.add_argument(
        "-t",
        "--type",
        help="Show information about load balancers or amphoras",
        choices=("lb", "amphora"),
        required=True,
    )
    parser.add_argument(
        "-o",
        "--output-format",
        help="Output format. (default: %(default)s)",
        choices=("plain", "rich", "json"),
        default="rich",
        required=False,
    )
    parser.add_argument("--name", help="Filter load balancers name", type=str, required=False)
    parser.add_argument(
        "--id", help="Filter load balancers id (UUID)", type=validate_uuid, required=False
    )
    parser.add_argument("--tags", help="Filter load balancers tags", type=str, required=False)
    parser.add_argument(
        "--flavor-id",
        help="Filter load balancers flavor id (UUID)",
        type=validate_uuid,
        required=False,
    )
    parser.add_argument(
        "--vip-address",
        help="Filter load balancers VIP address",
        type=validate_ip_address,
        required=False,
    )
    parser.add_argument(
        "--availability-zone", help="Filter load balancers AZ", type=str, required=False
    )
    parser.add_argument(
        "--vip-network-id",
        help="Filter load balancers network id (UUID)",
        type=validate_uuid,
        required=False,
    )
    parser.add_argument(
        "--vip-subnet-id",
        help="Filter load balancers subnet id (UUID)",
        type=validate_uuid,
        required=False,
    )
    parser.add_argument(
        "--details",
        help="Show all load balancers/amphora details. (default: %(default)s)",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "--no-members",
        help="Do not show load balancers pool members information. (default: %(default)s)",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "--max-workers",
        help=(
            f"Max number of concurrent threads to fetch members details "
            f"(1-{MAX_WORKERS_LIMIT}). (default: %(default)s)"
        ),
        type=validate_int_range(1, MAX_WORKERS_LIMIT),
        default=4,
        required=False,
    )

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    return args


def validate_int_range(min_val, max_val):
    """
    Argparse type function that validates integer input within a given range.

    Args:
        min_val (int): Minimum allowed integer value (inclusive).
        max_val (int): Maximum allowed integer value (inclusive).

    Raises:
        argparse.ArgumentTypeError: If the string cannot be converted to an integer
                                    or if the value is out of range.
    """

    def _check_value(value_str):
        try:
            value = int(value_str)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"Invalid integer: '{value_str!r}'") from exc

        if value < min_val or value > max_val:
            raise argparse.ArgumentTypeError(f"Value must be between {min_val} and {max_val}")
        return value

    return _check_value


def validate_uuid(value_str):
    """
    Argparse type function that checks whether a string is a valid UUID.

    Args:
        value_str (str): The value to validate.

    Returns:
        str: The UUID string if valid.

    Raises:
        argparse.ArgumentTypeError: If the value is not a valid UUID.
    """
    try:
        uuid.UUID(str(value_str))
        return value_str
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid UUID: {value_str!r}") from exc


def validate_ip_address(value_str):
    """
    Argparse type function that checks whether a string is a valid IP address.

    Args:
        value_str (str): The IP address to validate.

    Returns:
        str: The string if it is a valid IPv4/IPv6 address.

    Raises:
        argparse.ArgumentTypeError: If the string is not valid IP address.
    """
    try:
        ipaddress.ip_address(value_str)
        return value_str
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid IP address: {value_str!r}") from exc


def setup_logging(log_level):
    """Setup logging configuration."""
    datefmt = "%Y-%m-%d %H:%M:%S"
    msg_fmt = "%(asctime)s - %(module)s.%(funcName)s - [%(levelname)s] - %(message)s"

    formatter = logging.Formatter(
        fmt=msg_fmt,
        datefmt=datefmt,
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)


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
    log.debug("Retrieve load balancers filter: %s", filter_criteria)

    with formatter.status("Querying load balancers and applying filters..."):
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

    log_level = logging.DEBUG if args.debug else logging.WARNING
    setup_logging(log_level)
    log.debug("CMD line args: %s", args)

    if args.output_format == "rich" and not RICH_AVAILABLE:
        sys.exit(
            "Error: 'rich' library is not installed. "
            "Please install it or choose another output format."
        )

    # Initialize the formatter
    formatter = get_formatter(args.output_format)

    # Create an instance of OpenStackAPI
    try:
        openstackapi = OpenStackAPI(args.os_cloud)
    except RuntimeError as exc:
        sys.exit(f"Error: {exc}")

    try:
        filtered_lbs = query_openstack_lbs(openstackapi, args, formatter)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        log.debug("Error to query openstack:", exc_info=True)
        sys.exit(f"Error: {exc}")

    log.info("Found %d load balancer(s) to process.", len(filtered_lbs))

    if not filtered_lbs:
        formatter.print("No load balancer(s) found.")
        sys.exit(1)

    context = ProcessingContext(
        openstack_api=openstackapi,
        details=args.details,
        max_workers=args.max_workers,
        no_members=args.no_members,
        formatter=formatter,
    )
    log.debug("Process context: %s", context)

    for lb in filtered_lbs:
        if args.type == "amphora":
            amphora_info = AmphoraInfo(lb, context)
            amphora_info.display_amp_info()
        else:
            lb_info = LoadBalancerInfo(lb, context)
            lb_info.display_lb_info()


##############################################################################
# Run from command line
##############################################################################
if __name__ == "__main__":
    main()

# vim: ts=4
