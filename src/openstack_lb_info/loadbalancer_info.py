# -*- coding: utf-8 -*-
"""
Load Balancer Information Module
--------------------------------

This module provides classes for retrieving, organizing, and displaying detailed information
about OpenStack Load Balancers and their associated resources, such as listeners, pools,
health monitors, members, and amphorae. It uses the `OpenStackAPI` class for interacting
with the OpenStack environment and uses `OutputFormatter` instances to present the information
in various output formats (e.g., Rich text, plain text, JSON).

Classes:

- `LoadBalancerInfo`: Retrieves and displays detailed information about a specific Load Balancer,
  including its listeners, pools, health monitors, and members.

- `AmphoraInfo`: Extends `LoadBalancerInfo` to focus on retrieving and displaying information
  about the amphorae associated with a Load Balancer.
"""


class LoadBalancerInfo:
    """
    Provides information and structured display of OpenStack Load Balancers.
    """

    def __init__(self, openstack_api, lb, details, formatter):
        """
        Initialize a LoadBalancerInfo instance.

        Args:
            openstack_api (OpenStackAPI): An instance of `OpenStackAPI` for OpenStack interactions.
            lb (openstack.load_balancer.v2.load_balancer.LoadBalancer): The Load Balancer object.
            details (bool): If True, displays detailed attributes of the Load Balancer.
            formatter (OutputFormatter): An instance of a formatter class for output formatting.
        """
        self.lb = lb
        self.details = details
        self.formatter = formatter
        self.lb_tree = None
        self.openstack_api = openstack_api

    def create_lb_tree(self):
        """
        Create a tree representing Load Balancer information.

        Returns:
            Tree: A tree object representing Load Balancer information.
        """
        self.lb_tree = self.formatter.add_lb_to_tree(self.lb)
        if self.details:
            self.formatter.add_details_to_tree(self.lb_tree, self.lb.to_dict())

        return self.lb_tree

    def add_listener_info(self, parent_tree, listener_id):
        """
        Add information about a Listener to the Load Balancer tree.

        Args:
            listener_id (str): The ID of the Listener for which to retrieve and display
                information.

        Returns:
            None
        """
        with self.formatter.status(f"Getting Listener details id [b]{listener_id}[/b]"):
            listener = self.openstack_api.retrieve_listener(listener_id)

        if listener:
            listener_tree = self.formatter.add_listener_to_tree(parent_tree, listener)
            if self.details:
                self.formatter.add_details_to_tree(listener_tree, listener.to_dict())

            if listener.default_pool_id:
                self.add_pool_info(listener_tree, listener.default_pool_id)
            else:
                self.formatter.add_empty_node(listener_tree, "Pool")
        else:
            self.formatter.add_empty_node(parent_tree, "Listener")

    def add_pool_info(self, parent_tree, pool_id):
        """
        Add information about a Pool to the Load Balancer tree.

        Args:
            tree: The tree representing the Load Balancer.
            pool_id (str): The ID of the Pool for which to retrieve and display.

        Returns:
            None
        """
        with self.formatter.status(f"Getting Pool details id [b]{pool_id}[/b]"):
            pool = self.openstack_api.retrieve_pool(pool_id)

        if pool:
            pool_tree = self.formatter.add_pool_to_tree(parent_tree, pool)
            if self.details:
                self.formatter.add_details_to_tree(pool_tree, pool.to_dict())

            if pool.health_monitor_id:
                self.add_health_monitor_info(pool_tree, pool.health_monitor_id)
            else:
                self.formatter.add_empty_node(pool_tree, "Health Monitor")

            if pool.members:
                self.add_pool_members(pool_tree, pool.id, pool.members)
            else:
                self.formatter.add_empty_node(pool_tree, "Member")
        else:
            self.formatter.add_empty_node(parent_tree, "Pool")

    def add_health_monitor_info(self, parent_tree, health_monitor_id):
        """
        Add information about a Health Monitor to a Pool tree.

        Args:
            pool_tree: The tree representing the Pool.
            health_monitor_id (str): The ID of the Health Monitor.

        Returns:
            None
        """
        with self.formatter.status(f"Getting Health Monitor details id [b]{health_monitor_id}[/b]"):
            hm = self.openstack_api.retrieve_health_monitor(health_monitor_id)

        if hm:
            hm_tree = self.formatter.add_health_monitor_to_tree(parent_tree, hm)
            if self.details:
                self.formatter.add_details_to_tree(hm_tree, hm.to_dict())
        else:
            self.formatter.add_empty_node(parent_tree, "Health Monitor")

    def add_pool_members(self, parent_tree, pool_id, pool_members):
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
        for member_ref in pool_members:
            member_id = member_ref["id"]
            with self.formatter.status(f"Getting member details id [b]{member_id}[/b]"):
                member = self.openstack_api.retrieve_member(member_id, pool_id)

            if member:
                member_tree = self.formatter.add_member_to_tree(parent_tree, member)
                if self.details:
                    self.formatter.add_details_to_tree(member_tree, member.to_dict())
            else:
                self.formatter.add_empty_node(parent_tree, f"Member ({member_id})")

    def display_lb_info(self):
        """
        Display information about the Load Balancer.

        Returns:
            None
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
        self.formatter.print_tree(self.lb_tree)
        self.formatter.print("")


class AmphoraInfo(LoadBalancerInfo):
    """
    Provides information about Amphorae associated with an OpenStack Load Balancer.

    This class extends the LoadBalancerInfo class and adds functionality to retrieve
    and display information about Amphorae associated with an OpenStack
    Load Balancer.

    Class Attributes:
        images_name (dict): A dictionary to cache image names for Amphorae.
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
        image_name = AmphoraInfo.images_name.get(amphora.image_id, "N/A")

        # Get amphora server (instance) details
        with self.formatter.status(f"Getting server details [b]{amphora.compute_id}[/b]"):
            server = self.openstack_api.retrieve_server(amphora.compute_id)

        amphora_tree = self.formatter.add_amphora_to_tree(self.lb_tree, amphora, server, image_name)
        if self.details:
            self.formatter.add_details_to_tree(amphora_tree, amphora.to_dict())

    def display_amp_info(self):
        """
        Display information about amphorae associated with a load balancer.

        Returns:
            None
        """
        self.lb_tree = self.create_lb_tree()

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
