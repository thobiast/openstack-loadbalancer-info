# -*- coding: utf-8 -*-
"""
OpenStack API Interface Module
------------------------------

This module provides a class `OpenStackAPI` that serves as an interface for interacting with
various OpenStack services related to load balancing. It encapsulates the connection logic
to the OpenStack environment and offers methods to retrieve information about load balancers,
listeners, pools, health monitors, members, amphorae, servers, and images.
"""

import logging

import openstack

log = logging.getLogger(__name__)


class OpenStackAPI:
    """
    Provides an interface for querying OpenStack load balancer resources.
    """

    def __init__(self, os_cloud, verify=True, debug=False):
        """
        Initialize the OpenStackAPI instance and establish a connection.

        Args:
            os_cloud  (str): The name of the configuration to load from clouds.yaml.
                             If 'envvars', it loads config from environment variables
            verify   (bool): specifies if SSL certificates are verified (default: True)
            debug    (bool): Whether to enable debug logging.
        """
        log.debug("Create openstack connect to cloud: '%s'", os_cloud)
        openstack.enable_logging(debug=debug)
        try:
            self.os_conn = openstack.connect(cloud=os_cloud, verify=verify)
        except Exception as exc:
            log.debug("Openstack connection configuration failed:", exc_info=True)
            raise RuntimeError(f"Failed to connect to OpenStack: {exc}") from exc

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
        log.debug("Retrieving load balancers with filters: %s", filter_criteria)
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
        log.debug("Retrieving listener with ID: %s", listener_id)
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
        log.debug("Retrieving pool with ID: %s", pool_id)
        return self.os_conn.load_balancer.find_pool(pool_id)

    def retrieve_pools(self, loadbalancer_id):
        """
        Retrieve pools associated with an OpenStack load balancer.

        Args:
            loadbalancer_id (str): The ID of the load balancer for which pools are
                to be retrieved.

        Returns:
            Generator[openstack.load_balancer.v2.pool.Pool]: A generator of OpenStack
                pool objects representing the pools associated with the specified
                load balancer.
        """
        log.debug("Retrieving pools for load balancer ID: %s", loadbalancer_id)
        return self.os_conn.load_balancer.pools(loadbalancer_id=loadbalancer_id)

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
        log.debug("Retrieving health monitor with ID: %s", health_monitor_id)
        return self.os_conn.load_balancer.find_health_monitor(health_monitor_id)

    def retrieve_l7_policy(self, l7_policy_id):
        """
        Retrieve details of an L7 Policy.

        Args:
            l7_policy_id (str): The ID of the L7 Policy to retrieve.

        Returns:
            openstack.load_balancer.v2.l7_policy.L7Policy | None:
                The L7 Policy object if found, otherwise None.
        """
        log.debug("Retrieving L7 Policy with ID: %s", l7_policy_id)
        return self.os_conn.load_balancer.find_l7_policy(l7_policy_id)

    def retrieve_l7_rule(self, l7_rule_id, l7_policy_id, ignore_missing=True):
        """
        Retrieve details of an L7 Rule.

        Args:
            l7_rule_id (str): The ID of the L7 Rule to retrieve.
            l7_policy_id (str): The ID of the L7 Policy that the l7rule belongs to.
            ignore_missing (bool, optional): If True, returns None if the l7rule
                is not found. If False, raises an exception if the rule
                does not exist. Defaults to True.

        Returns:
            openstack.load_balancer.v2.l7_rule.L7Rule | None:
                The L7 Rule object if found, otherwise None.
        """
        log.debug("Retrieving L7 Rule %s for L7 Policy %s", l7_rule_id, l7_policy_id)
        return self.os_conn.load_balancer.find_l7_rule(
            l7_rule_id, l7_policy_id, ignore_missing=ignore_missing
        )

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
        log.debug("Retrieving member with ID: %s from pool ID: %s", member_id, pool_id)
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
        log.debug("Retrieving amphoraes from LB ID: %s", loadbalancer_id)
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
        log.debug("Retrieving compute server with ID: %s", server_id)
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
        log.debug("Retrieving image with IDs: %s", image_ids)
        return self.os_conn.image.images(id=image_ids)


# vim: ts=4
