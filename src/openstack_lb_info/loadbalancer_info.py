# -*- coding: utf-8 -*-
"""
Load Balancer Information Module
--------------------------------

This module provides classes for retrieving, organizing, and displaying detailed information
about OpenStack Load Balancers and their associated resources. It uses the `OpenStackAPI`
class for interacting with the OpenStack environment and uses `OutputFormatter` instances
to present the information in various output formats (e.g., Rich text, plain text, JSON).

Classes:

- `LoadBalancerInfo`: Retrieves and displays detailed information about a specific Load Balancer,
  including its listeners, pools, health monitors, and members.

- `AmphoraInfo`: Extends `LoadBalancerInfo` to focus on retrieving and displaying information
  about the amphorae associated with a Load Balancer.
"""
import concurrent.futures
import logging
from dataclasses import dataclass

from .formatters import OutputFormatter
from .openstack_api import OpenStackAPI

log = logging.getLogger(__name__)


@dataclass
class ProcessingContext:
    """
    Holds shared objects and configuration used during load balancer processing.

    Attributes:
        openstack_api (OpenStackAPI): An instance of `OpenStackAPI` for OpenStack interactions.
        details (bool): If True, displays detailed attributes of the Load Balancer.
        formatter (OutputFormatter): An instance of a formatter class for output formatting.
        max_workers (int): Max number of concurrent threads to fetch members details.
        no_members (bool): Do not show load balancer pool members information.
    """

    openstack_api: OpenStackAPI
    details: bool
    max_workers: int
    no_members: bool
    formatter: OutputFormatter


class LoadBalancerInfo:
    """
    Retrieves and displays information for a single OpenStack Load Balancer.
    """

    def __init__(self, lb, context):
        """
        Initialize a LoadBalancerInfo instance.

        Args:
            lb (openstack.load_balancer.v2.load_balancer.LoadBalancer): The Load Balancer object.
            context (ProcessingContext): A instance of ProcessingContext class.
        """
        self.lb = lb
        self.details = context.details
        self.formatter = context.formatter
        self.openstack_api = context.openstack_api
        self.max_workers = context.max_workers
        self.no_members = context.no_members
        # The root of the display tree for the formatter
        self.lb_tree = None
        log.info("Processing info for Load Balancer ID: %s (Name: %s)", self.lb.id, self.lb.name)

    def create_lb_tree(self):
        """
        Create the root of the display tree for the load balancer.

        This method instructs the formatter to create the main tree node
        and adds detailed attributes if requested.
        """
        self.lb_tree = self.formatter.add_lb_to_tree(self.lb)
        if self.details:
            self.formatter.add_details_to_tree(self.lb_tree, self.lb.to_dict())

    def add_listener_info(self, lb_tree, listener_id):
        """
        Add information about the Listener to the Load Balancer's tree.

        Args:
            lb_tree (object): The root tree node for the load balancer.
            listener_id (str): The ID of the Listener for which to retrieve and display
                information.
        """
        with self.formatter.status(f"Getting Listener details id [b]{listener_id}[/b]"):
            listener = self.openstack_api.retrieve_listener(listener_id)

        if listener:
            listener_tree = self.formatter.add_listener_to_tree(lb_tree, listener)
            if self.details:
                self.formatter.add_details_to_tree(listener_tree, listener.to_dict())

            if listener.default_pool_id:
                self.add_pool_info(listener_tree, listener.default_pool_id)
            else:
                self.formatter.add_empty_node(listener_tree, "Pool")
        else:
            self.formatter.add_empty_node(lb_tree, "Listener")

    def add_pool_info(self, listener_tree, pool_id):
        """
        Add information about the Pool to the listener's tree.

        Args:
            listener_tree (object): The tree representing the listener.
            pool_id (str): The ID of the Pool for which to retrieve and display.
        """
        with self.formatter.status(f"Getting Pool details id [b]{pool_id}[/b]"):
            pool = self.openstack_api.retrieve_pool(pool_id)

        if pool:
            pool_tree = self.formatter.add_pool_to_tree(listener_tree, pool)
            if self.details:
                self.formatter.add_details_to_tree(pool_tree, pool.to_dict())

            if pool.health_monitor_id:
                self.add_health_monitor_info(pool_tree, pool.health_monitor_id)
            else:
                self.formatter.add_empty_node(pool_tree, "Health Monitor")

            if not self.no_members:
                if pool.members:
                    self.add_pool_members(pool_tree, pool.id, pool.members)
                else:
                    self.formatter.add_empty_node(pool_tree, "Member")
        else:
            self.formatter.add_empty_node(listener_tree, "Pool")

    def add_health_monitor_info(self, pool_tree, health_monitor_id):
        """
        Add information about the Health Monitor to the pool's tree.

        Args:
            pool_tree: The tree representing the pool.
            health_monitor_id (str): The ID of the Health Monitor.
        """
        with self.formatter.status(f"Getting Health Monitor details id [b]{health_monitor_id}[/b]"):
            hm = self.openstack_api.retrieve_health_monitor(health_monitor_id)

        if hm:
            hm_tree = self.formatter.add_health_monitor_to_tree(pool_tree, hm)
            if self.details:
                self.formatter.add_details_to_tree(hm_tree, hm.to_dict())
        else:
            self.formatter.add_empty_node(pool_tree, "Health Monitor")

    def add_pool_members(self, pool_tree, pool_id, pool_members):
        """
        Add information about Members to the pool's tree.

        Args:
            pool_tree: The tree representing the Pool.
            pool_id (str): The ID of the Pool for which to retrieve Member information.
            pool_members (list): A list of dictionaries containing Member information,
                where each dictionary includes the Member's ID and additional details.
        """
        # Avoid spinning up extra idle threads
        max_workers = min(self.max_workers, len(pool_members))
        log.debug(
            "Using %s workers to fetch details of %s members (pool_id=%s)",
            max_workers,
            len(pool_members),
            pool_id,
        )

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create future for each member IDs
            futures_to_member_id = {
                executor.submit(self.openstack_api.retrieve_member, member["id"], pool_id): member[
                    "id"
                ]
                for member in pool_members
            }

            # Use the formatter's progress bar to track completion
            description = f"Getting members information for pool id: {pool_id}"

            progress_iterator = self.formatter.track_progress(
                sequence=concurrent.futures.as_completed(futures_to_member_id),
                description=description,
                total=len(futures_to_member_id),
            )

            for future in progress_iterator:
                member_id = futures_to_member_id[future]
                try:
                    member = future.result()
                    if member:
                        member_tree = self.formatter.add_member_to_tree(pool_tree, member)
                        if self.details:
                            self.formatter.add_details_to_tree(member_tree, member.to_dict())
                    else:
                        self.formatter.add_empty_node(pool_tree, f"Member ({member_id})")
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    self.formatter.add_empty_node(pool_tree, f"Member ({member_id} - Error: {exc})")

    def display_lb_info(self):
        """
        Fetch and display information about the Load Balancer.

        This is the main entry point for this class. It builds the display tree
        and prints it.
        """
        self.create_lb_tree()

        if not self.lb.listeners:
            self.formatter.add_empty_node(self.lb_tree, "Listener")
        else:
            for listener in self.lb.listeners:
                self.add_listener_info(self.lb_tree, listener["id"])

        self.formatter.rule(
            f"[b]Loadbalancer ID: {self.lb.id} [bright_blue]({self.lb.name})[/]",
            align="center",
        )
        log.info("Displaying final tree for Load Balancer ID: %s", self.lb.id)
        self.formatter.print_tree(self.lb_tree)
        self.formatter.print("")


class AmphoraInfo(LoadBalancerInfo):
    """
    Retrieves and displays Amphora information for a Load Balancer.

    This class extends LoadBalancerInfo to provide specific functionality for
    displaying information about Amphorae associated with a Load Balancer.

    Class Attributes:
        images_name (dict): A class-level cache for image names.
    """

    images_name = {}

    def get_images_name(self, image_ids):
        """
        Retrieve image names for a list of image IDs and cache the results.

        Args:
            image_ids (list): A list of image IDs for which to retrieve image names.

        Note:
            The retrieved image names are stored in the 'images_name' class attribute
            for future reference, avoiding redundant queries to the OpenStack.
        """
        # Checks the cache before making an API call
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
        """
        # Get image name for the image ID
        self.get_images_name([amphora.image_id])
        image_name = AmphoraInfo.images_name.get(amphora.image_id, "N/A")

        # Get amphora server (instance) details
        with self.formatter.status(f"Getting server details [b]{amphora.compute_id}[/b]"):
            server = self.openstack_api.retrieve_server(amphora.compute_id)

        amphora_tree = self.formatter.add_amphora_to_tree(self.lb_tree, amphora, server, image_name)
        if self.details:
            self.formatter.add_details_to_tree(amphora_tree, amphora.to_dict())

    def display_amp_info(self):
        """
        Fetch and display information about amphorae associated with a load balancer.

        This is the main entry point for this class. It builds the display tree
        and prints it.
        """
        self.create_lb_tree()

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


# vim: ts=4
