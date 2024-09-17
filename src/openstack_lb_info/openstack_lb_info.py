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
import contextlib
import ipaddress
import json
import re
import sys
import uuid
from abc import ABC, abstractmethod

import openstack

try:
    from rich.console import Console
    from rich.highlighter import ReprHighlighter
    from rich.tree import Tree

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


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

    validate_arguments(args, parser)

    return args


def validate_arguments(args, parser):
    """
    Validate command-line arguments.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.
        parser (argparse.ArgumentParser): Argument parser instance.

    Raises:
        SystemExit: If validation fails, the parser exits the script.
    """
    # Validate UUIDs parameters
    uuid_args = ["id", "vip_network_id", "vip_subnet_id", "flavor_id"]
    for arg_name in uuid_args:
        arg_value = getattr(args, arg_name)
        if arg_value and not is_valid_uuid(arg_value):
            parser.error(f"Invalid {arg_name.replace('_', '-')} format. Expected a UUID.")

    # Validate IP address
    if args.vip_address and not is_valid_ip_address(args.vip_address):
        parser.error("Invalid VIP address format. Expected a valid IP address.")


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
    Check if the parameter is a valid IP address.

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


class OutputFormatter(ABC):
    """Abstract base class for output formatters."""

    @abstractmethod
    def create_tree(self, name):
        """Create a tree structure for the output."""

    @abstractmethod
    def add_to_tree(self, tree, content):
        """Add content to the tree structure."""

    @abstractmethod
    def print_tree(self, tree):
        """Print the tree structure."""

    @abstractmethod
    def print(self, message):
        """Print a message."""

    @abstractmethod
    def status(self, message):
        """Display a status message."""

    @abstractmethod
    def line(self):
        """Print a line separator."""

    @abstractmethod
    def rule(self, title, align="center"):
        """Print a rule with a title."""

    @abstractmethod
    def format_status(self, status):
        """Format status text."""


class RichOutputFormatter(OutputFormatter):
    """Formatter using the Rich library."""

    def __init__(self):
        self.console = Console()
        self.highlighter = ReprHighlighter()

    def create_tree(self, name):
        return Tree(name)

    def add_to_tree(self, tree, content, highlight=False):
        if highlight:
            content = self.highlighter(content)
        return tree.add(content)

    def print_tree(self, tree):
        self.console.print(tree)

    def print(self, message):
        self.console.print(message)

    def status(self, message):
        return self.console.status(message)

    def line(self):
        self.console.line()

    def rule(self, title, align="center"):
        self.console.rule(title, align=align)

    def format_message(self, message):
        """Return the message as-is, preserving Rich formatting."""
        return message

    def format_status(self, status):
        status_colors = {
            "ACTIVE": "green",
            "ONLINE": "green",
            "PENDING": "yellow",
        }
        color = status_colors.get(status, "red")
        return f"[{color}]{status}[/{color}]"


class PlainOutputFormatter(OutputFormatter):
    """Formatter for plain text output."""

    def create_tree(self, name):
        return {"name": name, "children": []}

    def add_to_tree(self, tree, content, highlight=False):
        _ = highlight
        child_tree = {"name": self.format_message(content), "children": []}
        tree["children"].append(child_tree)
        return child_tree

    def print_tree(self, tree, level=0):
        indent = "    " * level
        print(f"{indent}{self.format_message(tree['name'])}")
        for child in tree.get("children", []):
            self.print_tree(child, level + 1)

    def print(self, message):
        print(self.format_message(message))

    def status(self, message):
        @contextlib.contextmanager
        def plain_status():
            # Remove Rich formatting codes from the message
            clean_message = self.format_message(message)
            print(f"[STATUS] {clean_message}")
            try:
                yield
            finally:
                print(f"[STATUS] Completed: {clean_message}")

        return plain_status()

    def line(self):
        print()

    def rule(self, title, align="center"):
        title = self.format_message(title)
        print(f"{title}")
        print("-" * len(title))

    def format_message(self, message):
        """Remove Rich text formatting tags from a message."""
        clean_message = re.sub(r"\[\/?[^\]]+\]", "", message)
        return clean_message

    def format_status(self, status):
        return status


class JSONOutputFormatter(OutputFormatter):
    """Formatter for JSON output."""

    def __init__(self):
        self.data = None

    def create_tree(self, name):
        # Remove Rich codes
        clean_name = self.format_message(name)
        self.data = {"name": clean_name, "children": []}
        return self.data

    def add_to_tree(self, tree, content, highlight=False):
        _ = highlight
        # Remove Rich codes
        clean_content = self.format_message(content)
        # Create a new node and add it to the tree's children
        child = {"name": clean_content, "children": []}
        tree["children"].append(child)
        return child

    def print_tree(self, tree):
        print(json.dumps(tree, indent=4))

    def print(self, message):
        # Remove Rich codes
        clean_message = self.format_message(message)
        # Not show empty prints
        if not clean_message:
            return
        # For consistency, wrap messages in a dict
        output = {"message": clean_message}
        print(json.dumps(output, indent=4))

    def status(self, message):
        return contextlib.nullcontext()

    def line(self):
        pass

    def rule(self, title, align="center"):
        pass

    def format_status(self, status):
        return status

    def format_message(self, message):
        """Remove Rich text formatting tags from a message."""
        if isinstance(message, str):
            clean_message = re.sub(r"\[\/?[^\]]+\]", "", message)
            return clean_message
        return message


class OpenStackAPI:
    """
    Provides an interface for querying OpenStack load balancer resources.

    Args:
        os_conn (openstack.connection.Connection): An established OpenStack connection
            for interacting with the OpenStack environment.
    """

    def __init__(self, os_conn):
        """
        Initialize the OpenStackAPI instance.

        Args:
            os_conn (openstack.connection.Connection): OpenStack connection.
        """
        self.os_conn = os_conn

    def retrieve_load_balancers(self, filter_criteria):
        """
        Retrieve a list of load balancers based on specified filter criteria.

        Args:
            filter_criteria (dict): A dictionary containing filter criteria to narrow
                down the search for load balancers. The criteria may include 'tags',
                'availability_zone', 'vip_network_id', 'vip_subnet_id', and 'id'.

        Returns:
            list: A list of OpenStack load balancer objects that match the specified
                filter criteria, or an empty list if no load balancers match the
                criteria.
        """
        filtered_lbs = self.os_conn.load_balancer.load_balancers(**filter_criteria)
        return filtered_lbs

    def retrieve_listener(self, listener_id):
        """
        Retrieve details of an OpenStack load balancer listener.

        Args:
            listener_id (str): The ID of the listener to be retrieved.

        Returns:
            openstack.load_balancer.v2.listener.Listener: An OpenStack load balancer
                listener object representing the listener with the specified ID, or
                None if the listener is not found.
        """
        return self.os_conn.load_balancer.find_listener(listener_id)

    def retrieve_pool(self, pool_id):
        """
        Retrieve details of an OpenStack load balancer pool.

        Args:
            pool_id (str): The ID of the pool to be retrieved.

        Returns:
            openstack.load_balancer.v2.pool.Pool: An OpenStack load balancer pool object
                representing the pool with the specified ID, or None if the pool is
                not found.
        """
        return self.os_conn.load_balancer.find_pool(pool_id)

    def retrieve_health_monitor(self, health_monitor_id):
        """
        Retrieve details of an OpenStack load balancer health monitor.

        Args:
            health_monitor_id (str): The ID of the health monitor to be retrieved.

        Returns:
            openstack.load_balancer.v2.health_monitor.HealthMonitor: An OpenStack load
                balancer health monitor object representing the health monitor with the
                specified ID, or None if the health monitor is not found.
        """
        return self.os_conn.load_balancer.find_health_monitor(health_monitor_id)

    def retrieve_member(self, member_id, pool_id):
        """
        Retrieve details of an load balancer member by its ID and associated pool.

        Args:
            member_id (str): The ID of the member to be retrieved.
            pool_id (str): The ID of the pool to which the member belongs.

        Returns:
            openstack.load_balancer.v2.member.Member: An OpenStack load balancer member
                object representing the member with the specified ID and associated
                pool, or None if the member is not found.
        """
        return self.os_conn.load_balancer.find_member(member_id, pool_id)

    def retrieve_amphoraes(self, loadbalancer_id):
        """
        Retrieve a list of amphorae associated with an OpenStack load balancer.

        Args:
            loadbalancer_id (str): The ID of the load balancer for which amphorae are to
                be retrieved.

        Returns:
            Generator[openstack.load_balancer.v2.amphora.Amphora]: A generator of
                OpenStack amphora objects representing the amphorae associated with
                the specified load balancer.
        """
        return self.os_conn.load_balancer.amphorae(loadbalancer_id=loadbalancer_id)

    def retrieve_server(self, server_id):
        """
        Retrieve detailed information about an OpenStack server.

        Args:
            server_id (str): The ID of the OpenStack server for which detailed
                information is to be retrieved.

        Returns:
            openstack.compute.v2.server.Server: An OpenStack server object representing
            the specified server.
        """
        return self.os_conn.compute.find_server(server_id)

    def retrieve_images(self, image_ids):
        """
        Retrieve detailed information about OpenStack images.

        Args:
            image_ids (list): A list of image IDs for which detailed information is to
                be retrieved.

        Returns:
            list: A list of OpenStack image objects representing the specified images.
        """
        return self.os_conn.image.images(id=image_ids)


class LoadBalancerInfo:
    """
    Provides information and structured display of OpenStack Load Balancers.

    Args:
        os_conn (openstack.connection.Connection): An established OpenStack connection.
        lb (openstack.load_balancer.v2.load_balancer.LoadBalancer): The LB object.
        details (bool): Whether to display detailed attributes of the Load Balancer.
        formatter (OutputFormatter): Formatter instance for output.
    """

    def __init__(self, os_conn, lb, details, formatter):
        """
        Initialize a LoadBalancerInfo instance.

        Args:
            os_conn (openstack.connection.Connection)
            lb (openstack.load_balancer.v2.load_balancer.LoadBalancer)
            details (bool)
            formatter (OutputFormatter): Formatter instance.
        """
        self.lb = lb
        self.details = details
        self.formatter = formatter
        self.lb_tree = None
        self.openstack_api = OpenStackAPI(os_conn)

    def create_lb_tree(self):
        """
        Create a tree representing Load Balancer information.

        Returns:
            Tree: A tree object representing Load Balancer information.
        """
        self.lb_tree = self.formatter.create_tree(
            f"LB:[bright_yellow] {self.lb.id}[/] "
            f"vip:[bright_cyan]{self.lb.vip_address}[/] "
            f"prov_status:{self.formatter.format_status(self.lb.provisioning_status)} "
            f"oper_status:{self.formatter.format_status(self.lb.operating_status)} "
            f"tags:[magenta]{self.lb.tags}[/]"
        )
        if self.details:
            self.add_all_attr_to_tree(self.lb, self.lb_tree)

        return self.lb_tree

    def add_health_monitor_info(self, pool_tree, health_monitor_id):
        """
        Add information about a Health Monitor to a Pool tree.

        Args:
            pool_tree: The tree representing the Pool.
            health_monitor_id (str): The ID of the Health Monitor.

        Returns:
            None
        """
        with self.formatter.status(f"Getting health monitor details id [b]{health_monitor_id}[/b]"):
            health_monitor = self.openstack_api.retrieve_health_monitor(health_monitor_id)

        if health_monitor:
            health_monitor_tree = self.formatter.add_to_tree(
                pool_tree,
                f"[b green]Health Monitor:[/] [b white]{health_monitor.id}[/] "
                f"type:[magenta]{health_monitor.type}[/magenta] "
                f"http_method:[magenta]{health_monitor.http_method}[/magenta] "
                f"http_codes:[magenta]{health_monitor.expected_codes}[/magenta] "
                f"url_path:[magenta]{health_monitor.url_path}[/magenta] "
                f"prov_status:{self.formatter.format_status(health_monitor.provisioning_status)} "
                f"oper_status:{self.formatter.format_status(health_monitor.operating_status)}",
            )

            if self.details:
                self.add_all_attr_to_tree(health_monitor, health_monitor_tree)
        else:
            self.formatter.add_to_tree(pool_tree, "[b green]Health Monitor:[/] None")

    def add_pool_members(self, pool_tree, pool_id, pool_members):
        """
        Add information about Members of a Pool to the Pool tree.

        Args:
            pool_tree: The tree representing the Pool.
            pool_id (str): The ID of the Pool for which to retrieve Member information.
            pool_members (list): A list of dictionaries containing Member information,
                where each dictionary includes the Member's ID and additional details.

        Returns:
            None
        """
        for member in pool_members:
            with self.formatter.status(f"Getting member details id [b]{member['id']}[/b]"):
                os_m = self.openstack_api.retrieve_member(member["id"], pool_id)

            member_tree = self.formatter.add_to_tree(
                pool_tree,
                f"[b green]Member:[/] [b white]{os_m.id}[/] "
                f"IP:[magenta]{os_m.address}[/magenta] "
                f"port:[magenta]{os_m.protocol_port}[/magenta] "
                f"weight:[magenta]{os_m.weight}[/magenta] "
                f"backup:[magenta]{os_m.backup}[/magenta] "
                f"prov_status:{self.formatter.format_status(os_m.provisioning_status)} "
                f"oper_status:{self.formatter.format_status(os_m.operating_status)}",
            )

            if self.details:
                self.add_all_attr_to_tree(os_m, member_tree)

    def add_pool_info(self, tree, pool_id):
        """
        Add information about a Pool to the Load Balancer tree.

        Args:
            tree: The tree representing the Load Balancer.
            pool_id (str): The ID of the Pool for which to retrieve and display.

        Returns:
            None
        """
        with self.formatter.status(f"Getting pool details id [b]{pool_id}[/b]"):
            pool = self.openstack_api.retrieve_pool(pool_id)

        pool_tree = self.formatter.add_to_tree(
            tree,
            f"[b green]Pool:[/] [b white]{pool.id}[/] "
            f"protocol:[magenta]{pool.protocol}[/magenta] "
            f"algorithm:[magenta]{pool.lb_algorithm}[/magenta] "
            f"prov_status:{self.formatter.format_status(pool.provisioning_status)} "
            f"oper_status:{self.formatter.format_status(pool.operating_status)} ",
        )
        if self.details:
            self.add_all_attr_to_tree(pool, pool_tree)

        if pool.health_monitor_id:
            self.add_health_monitor_info(pool_tree, pool.health_monitor_id)
        else:
            self.formatter.add_to_tree(pool_tree, "[b green]Health Monitor:[/] None")

        if pool.members:
            self.add_pool_members(pool_tree, pool.id, pool.members)
        else:
            self.formatter.add_to_tree(pool_tree, "[b green]Member:[/] None")

    def add_listener_info(self, listener_id):
        """
        Add information about a Listener to the Load Balancer tree.

        Args:
            listener_id (str): The ID of the Listener for which to retrieve and display
                information.

        Returns:
            None
        """
        with self.formatter.status(
            f"Getting listener details for loadbalancers "
            f"[b]{self.lb.id}[/b] listener: [b]{listener_id}[/b]"
        ):
            listener = self.openstack_api.retrieve_listener(listener_id)

        listener_tree = self.formatter.add_to_tree(
            self.lb_tree,
            f"[b green]Listener:[/] [b white]{listener.id}[/] "
            f"([blue b]{listener.name}[/]) "
            f"port:[cyan]{listener.protocol}/{listener.protocol_port}[/] "
            f"prov_status:{self.formatter.format_status(listener.provisioning_status)} "
            f"oper_status:{self.formatter.format_status(listener.operating_status)} ",
        )
        if self.details:
            self.add_all_attr_to_tree(listener, listener_tree)

        if listener.default_pool_id:
            self.add_pool_info(listener_tree, listener.default_pool_id)
        else:
            self.formatter.add_to_tree(listener_tree, "[b green]Pool:[/] None")

    def add_all_attr_to_tree(self, obj, tree):
        """
        Add all attributes of an object to a tree.

        This function iterates through all the attributes of a given Python object and
        adds them to a Rich tree. Each attribute is displayed in the
        format "attribute_name: value".

        Args:
            obj (object): The object whose attributes are to be added.
            tree: The tree to which the attributes will be added.
        """
        obj_dict = obj.to_dict()
        for attr in sorted(obj_dict):
            value = obj_dict[attr]
            content = f"{attr}: {value}"
            self.formatter.add_to_tree(tree, content, highlight=True)

    def display_lb_info(self):
        """
        Display information about the Load Balancer.

        Returns:
            None
        """
        self.create_lb_tree()

        if not self.lb.listeners:
            self.formatter.add_to_tree(self.lb_tree, "[b green]Listener:[/] None")
        else:
            for listener in self.lb.listeners:
                self.add_listener_info(listener["id"])

        self.formatter.rule(
            f"[b]Loadbalancer ID: {self.lb.id} [bright_blue]({self.lb.name})[/]",
            align="center",
        )
        self.formatter.print_tree(self.lb_tree)
        self.formatter.print("")


class AmphoraInfo(LoadBalancerInfo):
    """
    Provides information about Amphorae associated with an OpenStack Load Balancer.

    This class extends the LoadBalancerInfo class and adds functionality to retrieve
    and display information about Amphorae associated with an OpenStack
    Load Balancer.

    Args:
        os_conn (openstack.connection.Connection): An established OpenStack connection.
        lb (openstack.load_balancer.v2.load_balancer.LoadBalancer): The Load Balancer
            for which Amphora details are to be retrieved.
        details (bool): If True, displays detailed attributes of Amphorae.
        formatter (OutputFormatter): Formatter instance for output.

    Class Attributes:
        images_name (dict): A dictionary to cache image names for Amphorae.
    """

    images_name = {}

    def __init__(self, os_conn, lb, details, formatter):
        """
        Initialize an AmphoraInfo instance.

        Args:
            os_conn (openstack.connection.Connection): OpenStack connection.
            lb (openstack.load_balancer.v2.load_balancer.LoadBalancer): LB object.
            details (bool): Show detailed attributes if True.
            formatter (OutputFormatter): Formatter instance.
        """
        super().__init__(os_conn, lb, details, formatter)
        self.lb_tree = self.create_lb_tree()

    def get_images_name(self, image_ids):
        """
        Retrieve image names for a list of image IDs and cache the results.

        Args:
            image_ids (list): A list of image IDs for which to retrieve image names.

        Note:
            The retrieved image names are stored in the 'images_name' class attribute
            for future reference, avoiding redundant queries to the OpenStack.

        Returns:
            None
        """
        new_img_ids = [i for i in image_ids if i not in AmphoraInfo.images_name]
        if new_img_ids:
            with self.formatter.status(f"Getting image details [b]{new_img_ids}[/b]"):
                for image in self.openstack_api.retrieve_images(new_img_ids):
                    AmphoraInfo.images_name[image.id] = image.name

    def add_amphora_to_tree(self, amphora):
        """
        Add information about an amphora to a tree.

        This method retrieves detailed information about a single amphora associated
        with a load balancer and add it to the tree representing the load balancer.

        Args:
            amphora (openstack.load_balancer.v2.amphora.Amphora): The amphora for which
                to display detailed information.

        Returns:
            None
        """
        # Get image name for the image ID
        self.get_images_name([amphora.image_id])
        # Get amphora server (instance) details
        with self.formatter.status(f"Getting server details [b]{amphora.compute_id}[/b]"):
            server = self.openstack_api.retrieve_server(amphora.compute_id)

        if server:
            server_id = server.id
            server_flavor_name = server.flavor.name if server.flavor else "N/A"
            server_compute_host = server.compute_host
        else:
            server_id = "N/A"
            server_flavor_name = "N/A"
            server_compute_host = "N/A"

        # Add amphora to the load balancer tree
        amphora_tree = self.formatter.add_to_tree(
            self.lb_tree,
            f"[b green]amphora: [/]"
            f"[b white]{amphora.id} [/]"
            f"{amphora.role} "
            f"{amphora.status} "
            f"lb_network_ip:[green]{amphora.lb_network_ip} [/]"
            f"img:[magenta]{AmphoraInfo.images_name.get(amphora.image_id, 'N/A')}[/] "
            f"server:[magenta]{server_id}[/] "
            f"vm_flavor:[magenta]{server_flavor_name}[/] "
            f"compute host:([magenta]{server_compute_host}[/])",
        )
        if self.details:
            self.add_all_attr_to_tree(amphora, amphora_tree)

    def display_amp_info(self):
        """
        Display information about amphorae associated with a load balancer.

        Returns:
            None
        """

        with self.formatter.status(
            f"Getting amphora details for load balancer [b]{self.lb.id}[/b]"
        ):
            amphoraes = self.openstack_api.retrieve_amphoraes(self.lb.id)

        for amphora in amphoraes:
            self.add_amphora_to_tree(amphora)

        self.formatter.rule(
            f"[b]Loadbalancer ID: {self.lb.id} [bright_blue]({self.lb.name})[/]",
            align="center",
        )
        self.formatter.print_tree(self.lb_tree)
        self.formatter.print("")


def query_openstack_lbs(os_conn, args, formatter):
    """
    Query OpenStack Load Balancers based on user-defined filters.

    Args:
        os_conn (openstack.connection.Connection): An established OpenStack connection.
        args (argparse.Namespace): Parsed command-line arguments.
        formatter (OutputFormatter): Formatter instance.

    Returns:
        list: A list of OpenStack Load Balancer objects that match the specified
            filters, or an empty list if no load balancers match the criteria.
    """
    # Define filter criteria
    filter_criteria = {
        "tags": args.tags,
        "availability_zone": args.availability_zone,
        "vip_network_id": args.vip_network_id,
        "vip_subnet_id": args.vip_subnet_id,
        "flavor_id": args.flavor_id,
        "vip_address": args.vip_address,
    }
    if args.id:
        # Add the "id" key to the filter criteria only if specified
        filter_criteria["id"] = args.id

    openstackapi = OpenStackAPI(os_conn)
    with formatter.status("Quering load balancers..."):
        filtered_lbs_tmp = openstackapi.retrieve_load_balancers(filter_criteria)

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
        print(f"Error: Unknown output format '{output_format}'")
        sys.exit(1)


##############################################################################
# Main
##############################################################################
def main():
    """
    Main function to execute script.
    """

    args = parse_parameters()

    openstack.enable_logging(debug=False)
    os_conn = openstack.connect()

    if args.output_format == "rich" and not RICH_AVAILABLE:
        print(
            "Error: 'rich' library is not installed. "
            "Please install it or choose another output format."
        )
        sys.exit(1)

    # Initialize the formatter
    formatter = get_formatter(args.output_format)

    filtered_lbs = query_openstack_lbs(os_conn, args, formatter)

    if not filtered_lbs:
        formatter.print("No load balancer(s) found.")
        sys.exit(1)

    for lb in filtered_lbs:
        if args.type == "amphora":
            amphora_info = AmphoraInfo(os_conn, lb, args.details, formatter)
            amphora_info.display_amp_info()
        else:
            lb_info = LoadBalancerInfo(os_conn, lb, args.details, formatter)
            lb_info.display_lb_info()


##############################################################################
# Run from command line
##############################################################################
if __name__ == "__main__":
    main()

# vim: ts=4
