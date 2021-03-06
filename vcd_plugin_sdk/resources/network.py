# Copyright (c) 2020 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pyvcloud.vcd.gateway import Gateway
from pyvcloud.vcd.nat_rule import NatRule
from pyvcloud.vcd.dhcp_pool import DhcpPool
from pyvcloud.vcd.vdc_network import VdcNetwork
from pyvcloud.vcd.firewall_rule import FirewallRule
from pyvcloud.vcd.exceptions import EntityNotFoundException, NotFoundException

from .base import VCloudResource
from ..utils import underscore_to_camelcase
from ..exceptions import VCloudSDKException

DESTINATION = 'destination'
SOURCE = 'source'
GROUP_OBJECT_LIST = ['securitygroup', 'ipset', 'virtualmachine', 'network']
VNIC_GROUP_LIST = ['gatewayinterface']

ADD_NAT_RULE_TEST_VALUE = {
    'action': 'dnat',
    'original_address': '10.10.4.2',
    'translated_address': '11.11.4.2',
    'description': 'nat rule test value',
}

class VCloudNetwork(VCloudResource):

    def __init__(self,
                 network_name,
                 network_type,
                 connection=None,
                 vdc_name=None,
                 vapp_name=None,
                 kwargs=None):

        self.network_name = network_name or kwargs.get('network_name')
        self.network_type = network_type
        self.kwargs = kwargs
        if 'network_name' in self.kwargs:
            del self.kwargs['network_name']
        self._network = None

        super().__init__(connection, vdc_name, vapp_name)

    @property
    def network(self):
        if not self._network:
            try:
                self._network = self.get_network()
            except EntityNotFoundException:
                raise VCloudSDKException(
                    'Network {name} has not been initialized.'.format(
                        self.network_name))
        return self._network

    @property
    def allocated_addresses(self):
        return self.network.list_allocated_ip_address()

    @property
    def connected_vapps(self):
        return self.network.list_connected_vapps()

    def get_network(self, network_name=None, network_type=None):
        if network_name and not network_type:
            raise VCloudSDKException(
                'The method get_network requires both network_name and '
                'network_type parameters.')
        elif not network_name and not self.network_name:
            raise VCloudSDKException(
                'The method get_network requires a network_name parameter if '
                'self.network_name is not set.')

        if not network_name:
            network_name = self.network_name
        if not network_type:
            network_type = self.network_type

        if network_type == 'routed_vdc_network':
            network_resource = self.vdc.get_routed_orgvdc_network(
                name=network_name)
        elif network_type == 'isolated_vdc_network':
            network_resource = self.vdc.get_isolated_orgvdc_network(
                name=network_name)
        elif network_type == 'directly_connected_vdc_network':
            network_resource = self.vdc.get_direct_orgvdc_network(
                name=network_name)
        else:
            raise VCloudSDKException(
                'The property network_type {network_type} is not one of '
                '[\'routed_vdc_network\', '
                '\'isolated_vdc_network\', '
                '\'directly_connected_vdc_network\', '
                '\'vapp_network\]'.format(network_type=self.network_type))
        return VdcNetwork(self.client, resource=network_resource)

    def create(self):
        if self.network_type == 'routed_vdc_network':
            return self.vdc.create_routed_vdc_network(
                network_name=self.network_name, **self.kwargs)
        elif self.network_type == 'isolated_vdc_network':
            return self.vdc.create_isolated_vdc_network(
                network_name=self.network_name, **self.kwargs)
        elif self.network_type == 'directly_connected_vdc_network':
            return self.vdc.create_directly_connected_vdc_network(
                network_name=self.network_name, **self.kwargs)
        elif self.network_type == 'vapp_network':
            if not self.vapp:
                raise VCloudSDKException(
                    'The property network_type is vapp_network,'
                    'but a vapp was not provided.')
            return self.vapp.create_vapp_network(
                name=self.network_name, **self.kwargs)
        else:
            raise VCloudSDKException(
                'The property network_type {network_type} is not one of '
                '[\'routed_vdc_network\', '
                '\'isolated_vdc_network\', '
                '\'directly_connected_vdc_network\', '
                '\'vapp_network\]'.format(network_type=self.network_type))

    def delete(self):
        if self.network_type == 'routed_vdc_network':
            return self.vdc.delete_routed_orgvdc_network(self.network_name)
        elif self.network_type == 'isolated_vdc_network':
            return self.vdc.delete_isolated_orgvdc_network(self.network_name)
        elif self.network_type == 'directly_connected_vdc_network':
            return self.vdc.delete_direct_orgvdc_network(self.network_name)
        elif self.network_type == 'vapp_network':
            if not self.vapp:
                raise VCloudSDKException(
                    'The property network_type is vapp_network,'
                    'but a vapp was not provided.')
            return self.vapp.delete_vapp_network(self.network_name)
        else:
            raise VCloudSDKException(
                'The property network_type {network_type} is not one of '
                '[\'routed_vdc_network\', '
                '\'isolated_vdc_network\', '
                '\'directly_connected_vdc_network\', '
                '\'vapp_network\]'.format(network_type=self.network_type))

    def add_static_ip_pool_and_dns(self, **kwargs):
        return self.network.add_static_ip_pool_and_dns(**kwargs)

    def modify_static_ip_pool(self, **kwargs):
        return self.network.modify_static_ip_pool(**kwargs)

    def remove_static_ip_pool(self, **kwargs):
        return self.remove_static_ip_pool(**kwargs)


class VCloudGateway(VCloudResource):

    def __init__(self,
                 gateway_name,
                 connection=None,
                 vdc_name=None,
                 kwargs=None):

        self.gateway_name = gateway_name
        self.kwargs = kwargs
        self._gateway = None

        super().__init__(connection, vdc_name)

    @property
    def gateway(self):
        if self._gateway:
            self._gateway.reload()
        else:
            self._gateway = self.get_gateway()
        return self._gateway

    @property
    def firewall_rules(self):
        return self.gateway.get_firewall_rules_list()

    @property
    def firewall_objects(self):
        firewall_objects = {DESTINATION: {}, SOURCE: {}}
        for direction in firewall_objects.keys():
            for group_key in GROUP_OBJECT_LIST + VNIC_GROUP_LIST:
                firewall_objects[direction][group_key] = \
                    self.gateway.list_firewall_objects(direction, group_key)
        return firewall_objects

    @property
    def static_routes(self):
        result = self.gateway.get_static_routes()
        return result.items()

    @property
    def nat_rules(self):
        return self.gateway.list_nat_rules()

    @property
    def dhcp_pools(self):
        out_list = []
        dhcp_resource = self.gateway.get_dhcp()
        if hasattr(dhcp_resource.ipPools, 'ipPool'):
            for ip_pool in dhcp_resource.ipPools.ipPool:
                out_list.append(ip_pool)
        return out_list

    @property
    def dhcp_binding(self):
        return self.gateway.list_dhcp_binding()

    @property
    def ca_certificates(self):
        return self.gateway.list_ca_certificates()

    @property
    def crl_certificates(self):
        return self.gateway.list_crl_certificates()

    @property
    def external_network_ip_allocations(self):
        return self.gateway.list_external_network_ip_allocations()

    @property
    def exposed_data(self):
        return {
            'dhcp_pools': self.dhcp_pools,
            'dhcp_binding': self.dhcp_binding,
            'crl_certificates': self.crl_certificates,
            'ca_certificates': self.ca_certificates,
            'nat_rules': self.nat_rules,
            'static_routes': self.static_routes,
            'firewall_rules': self.firewall_rules,
            'firewall_objects': self.firewall_objects
        }


    def get_gateway(self, gateway_name=None):
        gateway_name = gateway_name or self.gateway_name
        gateway_resource = self.vdc.get_gateway(gateway_name)
        return Gateway(self.client, resource=gateway_resource)

    # FIREWALLS
    def create_firewall_rule(self,
                             rule_name,
                             _type='User',
                             source_values=None,
                             destination_values=None,
                             services=None,
                             action='accept',
                             enabled=True,
                             logging_enabled=False,
                             **kwargs):

        # pyvcloud actually has type,
        # but we're not putting that kind of crap in our code.
        _type = kwargs.get('type', _type)
        before_rules = self.get_list_of_rule_ids()
        self.gateway.add_firewall_rule(
            rule_name, action, _type, enabled, logging_enabled)
        new_rule = self.infer_rule(rule_name, before_rules)
        new_rule.edit(source_values, destination_values, services)
        return new_rule.info_firewall_rule()

    def delete_firewall_rule(self, rule_name, rule_id):
        firewall_rule = self.infer_rule(rule_name, [rule_id], match=True)
        firewall_rule.delete()

    def get_list_of_rule_ids(self):
        all_rules = []
        for firewall_rules in self.gateway.get_firewall_rules():
            for firewall_rule in firewall_rules.firewallRules.firewallRule:
                all_rules.append(firewall_rule.id)
        return all_rules

    def infer_rule(self, rule_name, rule_ids=None, match=False):
        for firewall_rule_id in self.get_list_of_rule_ids():
            if not match and firewall_rule_id not in rule_ids:
                rule = FirewallRule(self.client,
                                    self.gateway_name,
                                    resource_id=firewall_rule_id)
                rule._reload()
                if rule_name == rule.resource.name:
                    return rule
            elif match and firewall_rule_id in rule_ids:
                rule = FirewallRule(self.client,
                                    self.gateway_name,
                                    resource_id=firewall_rule_id)
                rule._reload()
                if rule_name == rule.resource.name:
                    return rule

    # NATS
    def create_nat_rule(self, nat_definition=None):
        nat_definition = nat_definition or ADD_NAT_RULE_TEST_VALUE
        self.gateway.add_nat_rule(**nat_definition)
        return self.get_nat_rule_from_definition(nat_definition)

    def delete_nat_rule(self, nat_id=None, nat_definition=None):
        nat_rule = None
        if nat_definition:
            nat_rule = self.get_nat_rule_from_definition(nat_definition)
        elif nat_id:
            nat_rule = NatRule(self.client, self.gateway_name, rule_id=nat_id)
        elif not nat_rule:
            raise VCloudSDKException(
                'Unable to find nat rule for deletion, because neither '
                'nat_id {nat_id}, nor nat_definition {definition} '
                'resolved to any known rules for gateway {gateway}.'.format(
                    nat_id=nat_id,
                    definition=nat_definition,
                    gateway=self.gateway_name))
        return nat_rule.delete_nat_rule()

    def get_nat_rule_from_definition(self, nat_definition):
        for rule in self.gateway.list_nat_rules():
            nat_rule = NatRule(
                self.client, self.gateway_name, rule_id=rule['ID'])
            if self.compare_nat_rule(nat_rule.get_nat_rule_info(), nat_definition):
               return nat_rule.get_nat_rule_info()
        return {}

    @staticmethod
    def compare_nat_rule(rule_info, definition):
        for k, v in definition.items():
            if k == 'ID':
                continue
            if rule_info[underscore_to_camelcase(k)] != v:
                return False
        return True

    # DHCP POOLS
    def add_dhcp_pool(self, **pool_definition):
        self.gateway.add_dhcp_pool(**pool_definition)
        ip_pool = self.get_dhcp_pool_from_ip_range(
            pool_definition.get('ip_range'))
        return ip_pool.get_pool_info()

    def delete_dhcp_pool(self, **pool_definition):
        ip_pool = self.get_dhcp_pool_from_ip_range(
            pool_definition.get('ip_range'))
        return ip_pool.delete_pool()

    def get_dhcp_pool_from_ip_range(self, ip_range):
        for dhcp_pool in self.dhcp_pools:
            if dhcp_pool.ipRange == ip_range:
                return DhcpPool(self.client,
                                self.gateway_name,
                                resource_id=dhcp_pool.poolId)

    # DHCP BINDINGS
    # def add_dchp_binding(self, **binding_definition):
    #     return self.gateway.add_dhcp_binding(**binding_definition)
    #
