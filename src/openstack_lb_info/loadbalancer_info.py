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

    Class Attributes:
        images_name (dict): A dictionary to cache image names for Amphorae.
    """

    images_name = {}

    def __init__(self, openstack_api, lb, details, formatter):
        """
        Initialize an AmphoraInfo instance.

        Args:
            openstack_api (OpenStackAPI): An instance of `OpenStackAPI` for OpenStack interactions.
            lb (openstack.load_balancer.v2.load_balancer.LoadBalancer): The Load Balancer object.
            details (bool): If True, displays detailed attributes of the Amphorae.
            formatter (OutputFormatter): An instance of a formatter class for output formatting.
        """
        super().__init__(openstack_api, lb, details, formatter)
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


# vim: ts=4
