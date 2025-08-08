# -*- coding: utf-8 -*-
"""
Output Formatters Module
------------------------

This module provides classes for formatting and displaying output in different formats,
including Rich text, plain text, and JSON. It defines an abstract base class `OutputFormatter`
and concrete implementations for each output format. These formatters are used to present
information about OpenStack resources in a user-friendly and structured manner.
"""

import contextlib
import json
import re
from abc import ABC, abstractmethod

try:
    from rich.console import Console
    from rich.highlighter import ReprHighlighter
    from rich.tree import Tree

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class OutputFormatter(ABC):
    """Abstract base class for output formatters."""

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

    @abstractmethod
    def add_details_to_tree(self, tree, details_dict):
        """Adds all attributes from an object to the tree."""

    @abstractmethod
    def add_empty_node(self, tree, resource_name):
        """Adds a placeholder for a missing resource."""

    @abstractmethod
    def add_lb_to_tree(self, lb):
        """Create and return the root tree for the Load Balancer."""

    @abstractmethod
    def add_listener_to_tree(self, parent_tree, listener):
        """Adds a formatted listener node to the tree."""

    @abstractmethod
    def add_pool_to_tree(self, parent_tree, pool):
        """Adds a formatted pool node to the tree."""

    @abstractmethod
    def add_health_monitor_to_tree(self, parent_tree, hm):
        """Adds a formatted health monitor node to the tree."""

    @abstractmethod
    def add_member_to_tree(self, parent_tree, member):
        """Adds a formatted member node to the tree."""

    @abstractmethod
    def add_amphora_to_tree(self, parent_tree, amphora, server, image_name):
        """Adds a formatted amphora node to the tree."""


class RichOutputFormatter(OutputFormatter):
    """Formatter using the Rich library."""

    def __init__(self):
        self.console = Console()
        self.highlighter = ReprHighlighter()

    def _create_tree(self, name):
        return Tree(name)

    def _add_to_tree(self, tree, content, highlight=False):
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

    def format_status(self, status):
        status_colors = {
            "ACTIVE": "green",
            "ONLINE": "green",
            "PENDING": "yellow",
        }
        color = status_colors.get(status, "red")
        return f"[{color}]{status}[/{color}]"

    def add_details_to_tree(self, tree, details_dict):
        for attr in sorted(details_dict):
            value = details_dict[attr]
            content = f"{attr}: {value}"
            self._add_to_tree(tree, content, highlight=True)

    def add_empty_node(self, tree, resource_name):
        self._add_to_tree(tree, f"[b green]{resource_name}:[/] None")

    def add_lb_to_tree(self, lb):
        message = (
            f"LB:[bright_yellow] {lb.id}[/] "
            f"vip:[bright_cyan]{lb.vip_address}[/] "
            f"prov_status:{self.format_status(lb.provisioning_status)} "
            f"oper_status:{self.format_status(lb.operating_status)} "
            f"tags:[magenta]{lb.tags}[/]"
        )
        return self._create_tree(message)

    def add_listener_to_tree(self, parent_tree, listener):
        message = (
            f"[b green]Listener:[/] [b white]{listener.id}[/] "
            f"([blue b]{listener.name}[/]) "
            f"port:[cyan]{listener.protocol}/{listener.protocol_port}[/] "
            f"prov_status:{self.format_status(listener.provisioning_status)} "
            f"oper_status:{self.format_status(listener.operating_status)}"
        )
        return self._add_to_tree(parent_tree, message)

    def add_pool_to_tree(self, parent_tree, pool):
        message = (
            f"[b green]Pool:[/] [b white]{pool.id}[/] "
            f"protocol:[magenta]{pool.protocol}[/magenta] "
            f"algorithm:[magenta]{pool.lb_algorithm}[/magenta] "
            f"prov_status:{self.format_status(pool.provisioning_status)} "
            f"oper_status:{self.format_status(pool.operating_status)}"
        )
        return self._add_to_tree(parent_tree, message)

    def add_health_monitor_to_tree(self, parent_tree, hm):
        message = (
            f"[b green]Health Monitor:[/] [b white]{hm.id}[/] "
            f"type:[magenta]{hm.type}[/magenta] "
            f"http_method:[magenta]{hm.http_method}[/magenta] "
            f"http_codes:[magenta]{hm.expected_codes}[/magenta] "
            f"url_path:[magenta]{hm.url_path}[/magenta] "
            f"prov_status:{self.format_status(hm.provisioning_status)} "
            f"oper_status:{self.format_status(hm.operating_status)}"
        )
        return self._add_to_tree(parent_tree, message)

    def add_member_to_tree(self, parent_tree, member):
        message = (
            f"[b green]Member:[/] [b white]{member.id}[/] "
            f"IP:[magenta]{member.address}[/magenta] "
            f"port:[magenta]{member.protocol_port}[/magenta] "
            f"weight:[magenta]{member.weight}[/magenta] "
            f"backup:[magenta]{member.backup}[/magenta] "
            f"prov_status:{self.format_status(member.provisioning_status)} "
            f"oper_status:{self.format_status(member.operating_status)}"
        )
        return self._add_to_tree(parent_tree, message)

    def add_amphora_to_tree(self, parent_tree, amphora, server, image_name):
        server_id = server.id if server else "N/A"
        server_flavor_name = server.flavor.name if server and server.flavor else "N/A"
        server_compute_host = server.compute_host if server else "N/A"

        message = (
            f"[b green]amphora: [/]"
            f"[b white]{amphora.id} [/]"
            f"{amphora.role} "
            f"{amphora.status} "
            f"lb_network_ip:[green]{amphora.lb_network_ip} [/]"
            f"img:[magenta]{image_name}[/] "
            f"server:[magenta]{server_id}[/] "
            f"vm_flavor:[magenta]{server_flavor_name}[/] "
            f"compute host:([magenta]{server_compute_host}[/])"
        )
        return self._add_to_tree(parent_tree, message)


class PlainOutputFormatter(OutputFormatter):
    """Formatter for plain text output."""

    def _create_tree(self, name):
        return {"name": name, "children": []}

    def _add_to_tree(self, tree, content):
        child_tree = {"name": content, "children": []}
        tree["children"].append(child_tree)
        return child_tree

    def print_tree(self, tree, level=0):
        indent = "    " * level
        print(f"{indent}{tree['name']}")
        for child in tree.get("children", []):
            self.print_tree(child, level + 1)

    def print(self, message):
        print(message)

    def status(self, message):
        @contextlib.contextmanager
        def plain_status():
            print(f"[STATUS] {message}")
            try:
                yield
            finally:
                print(f"[STATUS] Completed: {message}")

        return plain_status()

    def line(self):
        print()

    def rule(self, title, align="center"):
        clean_title = re.sub(r"\[\/?[^\]]+\]", "", title)
        print(f"{clean_title}")
        print("-" * len(clean_title))

    def format_status(self, status):
        return status

    def add_details_to_tree(self, tree, details_dict):
        for attr in sorted(details_dict):
            value = details_dict[attr]
            content = f"{attr}: {value}"
            self._add_to_tree(tree, content)

    def add_empty_node(self, tree, resource_name):
        self._add_to_tree(tree, f"{resource_name}: None")

    def add_lb_to_tree(self, lb):
        message = (
            f"LB: {lb.id} "
            f"vip:{lb.vip_address} "
            f"prov_status:{self.format_status(lb.provisioning_status)} "
            f"oper_status:{self.format_status(lb.operating_status)} "
            f"tags:{lb.tags}"
        )
        return self._create_tree(message)

    def add_listener_to_tree(self, parent_tree, listener):
        message = (
            f"Listener: {listener.id} ({listener.name}) "
            f"port:{listener.protocol}/{listener.protocol_port} "
            f"prov_status:{self.format_status(listener.provisioning_status)} "
            f"oper_status:{self.format_status(listener.operating_status)}"
        )
        return self._add_to_tree(parent_tree, message)

    def add_pool_to_tree(self, parent_tree, pool):
        message = (
            f"Pool: {pool.id} "
            f"protocol:{pool.protocol} "
            f"algorithm:{pool.lb_algorithm} "
            f"prov_status:{self.format_status(pool.provisioning_status)} "
            f"oper_status:{self.format_status(pool.operating_status)}"
        )
        return self._add_to_tree(parent_tree, message)

    def add_health_monitor_to_tree(self, parent_tree, hm):
        message = (
            f"Health Monitor: {hm.id} "
            f"type:{hm.type} "
            f"http_method:{hm.http_method} "
            f"http_codes:{hm.expected_codes} "
            f"url_path:{hm.url_path} "
            f"prov_status:{self.format_status(hm.provisioning_status)} "
            f"oper_status:{self.format_status(hm.operating_status)}"
        )
        return self._add_to_tree(parent_tree, message)

    def add_member_to_tree(self, parent_tree, member):
        message = (
            f"Member: {member.id} "
            f"IP:{member.address} "
            f"port:{member.protocol_port} "
            f"weight:{member.weight} "
            f"backup:{member.backup} "
            f"prov_status:{self.format_status(member.provisioning_status)} "
            f"oper_status:{self.format_status(member.operating_status)}"
        )
        return self._add_to_tree(parent_tree, message)

    def add_amphora_to_tree(self, parent_tree, amphora, server, image_name):
        server_id = server.id if server else "N/A"
        server_flavor_name = server.flavor.name if server and server.flavor else "N/A"
        server_compute_host = server.compute_host if server else "N/A"
        message = (
            f"amphora: {amphora.id} {amphora.role} {amphora.status} "
            f"lb_network_ip:{amphora.lb_network_ip} "
            f"img:{image_name} "
            f"server:{server_id} "
            f"vm_flavor:{server_flavor_name} "
            f"compute host:({server_compute_host})"
        )
        return self._add_to_tree(parent_tree, message)


class JSONOutputFormatter(OutputFormatter):
    """Formatter for JSON output."""

    def __init__(self):
        self.data = None

    def print_tree(self, tree):
        print(json.dumps(tree, indent=4))

    def print(self, message):
        if not message:
            return
        output = {"message": message}
        print(json.dumps(output, indent=4))

    def status(self, message):
        return contextlib.nullcontext()

    def line(self):
        pass

    def rule(self, title, align="center"):
        pass

    def format_status(self, status):
        return status

    def _add_node_from_obj(self, parent_node, node_type, resource_obj):
        node = resource_obj.to_dict()
        node["type"] = node_type
        if "children" not in node:
            node["children"] = []
        parent_node["children"].append(node)
        return node

    def add_details_to_tree(self, tree, details_dict):
        pass

    def add_empty_node(self, tree, resource_name):
        tree["children"].append({f"{resource_name.lower().replace(' ', '_')}": None})

    def add_lb_to_tree(self, lb):
        root_node = lb.to_dict()
        root_node["type"] = "loadbalancer"
        root_node["children"] = []
        return root_node

    def add_listener_to_tree(self, parent_tree, listener):
        return self._add_node_from_obj(parent_tree, "listener", listener)

    def add_pool_to_tree(self, parent_tree, pool):
        return self._add_node_from_obj(parent_tree, "pool", pool)

    def add_health_monitor_to_tree(self, parent_tree, hm):
        return self._add_node_from_obj(parent_tree, "health_monitor", hm)

    def add_member_to_tree(self, parent_tree, member):
        return self._add_node_from_obj(parent_tree, "member", member)

    def add_amphora_to_tree(self, parent_tree, amphora, server, image_name):
        node = amphora.to_dict()
        node["type"] = "amphora"
        node["image_name"] = image_name
        if server:
            node["server_details"] = {
                "id": server.id,
                "flavor": server.flavor.name if server.flavor else "N/A",
                "compute_host": server.compute_host,
            }
        else:
            node["server_details"] = None
        parent_tree["children"].append(node)
        return node


# vim: ts=4
