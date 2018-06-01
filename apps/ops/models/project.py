# -*- coding: utf-8 -*-
#
import uuid
from collections import defaultdict

from django.utils.translation import ugettext_lazy as _
from django.db import models

from users.models import User
from common.utils import get_object_or_none
from perms.utils import AssetPermissionUtil

__all__ = ['Project']


class Project(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    assets = models.ManyToManyField('assets.Asset', verbose_name=_("Asset"))
    nodes = models.ManyToManyField('assets.Node', verbose_name=_("Node"))
    inventory = models.TextField()
    description = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Description"))
    created_by = models.CharField(max_length=128, blank=True, null=True, default='')
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def get_system_hosts(self):
        nodes = defaultdict(dict)
        _assets = self.assets.all().prefetch_related('nodes', 'systemuser_set')
        _nodes = self.nodes.all().prefetch_related('assets', 'systemuser_set')
        for node in _nodes:
            node_assets = node.get_assets()
            node_system_users = node.systemuser_set.all()
            for asset in node_assets:
                run_user = set(node_system_users)
                run_user.add(asset.admin_user)
                if asset in nodes[node]:
                    nodes[node][asset].update(run_user)
                else:
                    nodes[node][asset] = run_user
        for asset in _assets:
            asset_nodes = asset.get_nodes()
            asset_system_users = asset.systemuser_set.all()
            for node in asset_nodes:
                run_user = set(asset_system_users)
                run_user.add(asset.admin_user)
                if asset in nodes[node]:
                    nodes[node][asset].update(run_user)
                else:
                    nodes[node][asset] = run_user
        return nodes

    def get_user_hosts(self):
        nodes = defaultdict(dict)
        user = get_object_or_none(User, username=self.created_by)
        util = AssetPermissionUtil(user)
        assets_granted = util.get_assets()
        nodes_granted = util.get_nodes_with_assets()
        for node in self.nodes.all():
            if node in nodes_granted:
                nodes[node] = nodes_granted[node]
        for asset in self.assets.all().prefetch_related('nodes'):
            if asset not in assets_granted:
                continue
            for node in asset.nodes.all():
                if asset in nodes[node]:
                    nodes[node][asset].update(assets_granted[asset])
                else:
                    nodes[node][asset] = set(assets_granted[asset])
        return nodes

    def clean_hosts(self):
        if self.created_by.lower() == 'system':
            return self.get_system_hosts()
        else:
            return self.get_user_hosts()

    def parse_inventory(self):
        pass

    def gen_inventory(self):
        pass
