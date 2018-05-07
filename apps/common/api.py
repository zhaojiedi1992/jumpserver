# -*- coding: utf-8 -*-
#
import json

from rest_framework.views import Response, APIView
from ldap3 import Server, Connection
from django.core.mail import get_connection, send_mail
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from aliyunsdkcore.client import AcsClient
from aliyunsdkecs.request.v20140526 import DescribeInstancesRequest
from hashlib import md5
from common.utils import get_logger

from assets.models import Node, Asset
from .permissions import IsSuperUser
from .serializers import MailTestSerializer, LDAPTestSerializer
from .forms import CloudSettingForm

logger = get_logger(__file__)

class MailTestingAPI(APIView):
    permission_classes = (IsSuperUser,)
    serializer_class = MailTestSerializer
    success_message = _("Test mail sent to {}, please check")

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email_host_user = serializer.validated_data["EMAIL_HOST_USER"]
            kwargs = {
                "host": serializer.validated_data["EMAIL_HOST"],
                "port": serializer.validated_data["EMAIL_PORT"],
                "username": serializer.validated_data["EMAIL_HOST_USER"],
                "password": serializer.validated_data["EMAIL_HOST_PASSWORD"],
                "use_ssl": serializer.validated_data["EMAIL_USE_SSL"],
                "use_tls": serializer.validated_data["EMAIL_USE_TLS"]
            }
            connection = get_connection(timeout=5, **kwargs)
            try:
                connection.open()
            except Exception as e:
                return Response({"error": str(e)}, status=401)

            try:
                send_mail("Test", "Test smtp setting", email_host_user,
                          [email_host_user], connection=connection)
            except Exception as e:
                return Response({"error": str(e)}, status=401)

            return Response({"msg": self.success_message.format(email_host_user)})
        else:
            return Response({"error": str(serializer.errors)}, status=401)


class LDAPTestingAPI(APIView):
    permission_classes = (IsSuperUser,)
    serializer_class = LDAPTestSerializer
    success_message = _("Test ldap success")

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            host = serializer.validated_data["AUTH_LDAP_SERVER_URI"]
            bind_dn = serializer.validated_data["AUTH_LDAP_BIND_DN"]
            password = serializer.validated_data["AUTH_LDAP_BIND_PASSWORD"]
            use_ssl = serializer.validated_data.get("AUTH_LDAP_START_TLS", False)
            search_ou = serializer.validated_data["AUTH_LDAP_SEARCH_OU"]
            search_filter = serializer.validated_data["AUTH_LDAP_SEARCH_FILTER"]
            attr_map = serializer.validated_data["AUTH_LDAP_USER_ATTR_MAP"]

            try:
                attr_map = json.loads(attr_map)
            except json.JSONDecodeError:
                return Response({"error": "AUTH_LDAP_USER_ATTR_MAP not valid"}, status=401)

            server = Server(host, use_ssl=use_ssl)
            conn = Connection(server, bind_dn, password)
            try:
                conn.bind()
            except Exception as e:
                return Response({"error": str(e)}, status=401)

            ok = conn.search(search_ou, search_filter % ({"user": "*"}),
                             attributes=list(attr_map.values()))
            if not ok:
                return Response({"error": "Search no entry matched"}, status=401)

            users = []
            for entry in conn.entries:
                user = {}
                for attr, mapping in attr_map.items():
                    if hasattr(entry, mapping):
                        user[attr] = getattr(entry, mapping)
                users.append(user)
            if len(users) > 0:
                return Response({"msg": _("Match {} s users").format(len(users))})
            else:
                return Response({"error": "Have user but attr mapping error"}, status=401)
        else:
            return Response({"error": str(serializer.errors)}, status=401)


class DjangoSettingsAPI(APIView):
    def get(self, request):
        if not settings.DEBUG:
            return Response('Only debug mode support')

        configs = {}
        for i in dir(settings):
            if i.isupper():
                configs[i] = str(getattr(settings, i))
        return Response(configs)


class CloudOperatingAPI(APIView):

    @staticmethod
    def delete(request):
        """ Delete a cloud info by name"""

        name = request.data.get('name', None)
        succeed = CloudSettingForm.delete_info_by_name(name)
        msg = _("Delete successfully!")
        if not succeed:
            msg = _("Delete failed!")
        return Response({'msg': msg, 'succeed': succeed})

    def post(self, request):
        """ Import Assets from cloud """

        name = request.data.get('name', None)
        cloud_info = self.get_cloud_info(name)

        if cloud_info.get('provider', None) == "aliyun":
            return self.import_asset_from_aliyun(cloud_info)
        else:
            return Response({'msg': _("Cloud server error!"), 'succeed': False})

    def import_asset_from_aliyun(self, cloud_info):
        region_instances_dict = self.get_region_instances_dict_from_aliyun(cloud_info)
        if region_instances_dict:
            succeed = self.save(region_instances_dict, cloud_info)
            if succeed:
                return Response({'msg': _("Import successfully!"), 'succeed': True})
        return Response({'msg': _("Import failed!"), 'succeed': False})

    def get_already_exist_node(self, separator, root_children, node_str):
        for children in root_children:
            if children.full_value == node_str:
                return children
        else:
            end = node_str.rfind(separator)
            if end == -1:
                return Node.root()
            return self.get_already_exist_node(separator, root_children, node_str[:end])

    def get_or_create_node(self, node_str, cloud_root_node_name,
                           separator, region, name, provider):
        root_children = Node.root().get_all_children()
        exist_node = self.get_already_exist_node(separator, root_children, node_str)
        count = exist_node.full_value.count(separator)
        if count == 4:
            return exist_node
        elif count == 3:
            return exist_node.create_child(value=region)
        elif count == 2:
            return exist_node.create_child(value=name)\
                .create_child(value=region)
        elif count == 1:
            return exist_node.create_child(value=provider)\
                .create_child(value=name)\
                .create_child(value=region)
        else:
            return exist_node.create_child(value=cloud_root_node_name)\
                .create_child(value=provider)\
                .create_child(value=name)\
                .create_child(value=region)

    @staticmethod
    def get_region_instances_dict_from_aliyun(cloud_info):
        access_key_id = cloud_info.get('access_key_id', None)
        access_key_secret = cloud_info.get('access_key_secret', None)
        region_id_list = cloud_info.get('regions', {}).keys()
        region_instances_dict = {}
        page_size = 10

        for region_id in region_id_list:
            instances_list = []
            client = AcsClient(access_key_id, access_key_secret, region_id)
            request = DescribeInstancesRequest.DescribeInstancesRequest()
            try:
                info = client.do_action_with_exception(request)
                total_count = json.loads(info.decode()).get('TotalCount')
                import math
                total_pages = math.ceil(total_count/page_size)
                for page in range(1, int(total_pages)+1):
                    request.set_PageNumber(page)
                    request.set_PageSize(page_size)
                    info = client.do_action_with_exception(request)
                    info = json.loads(info)
                    instances_list.extend(
                        info.get('Instances', None).get('Instance', None)
                    )
                if instances_list:
                    region_instances_dict.update({region_id: instances_list})

            except Exception as e:
                logger.error(e)
                return {}
        return region_instances_dict

    def save(self, region_instances_dict, cloud_info):
        separator = ' / '
        cloud_root_node_name = '自动获取'
        root_node_name = Node.root().value
        name = cloud_info.get('name', None)
        provider = cloud_info.get('provider', None)

        for region_id, instances_list in region_instances_dict.items():
            region_name = cloud_info.get('regions', None)\
                .get(region_id, None)
            node_str = separator.join(
                [root_node_name, cloud_root_node_name, provider, name, region_name]
            )
            node = self.get_or_create_node(
                node_str, cloud_root_node_name=cloud_root_node_name,
                separator=separator, region=region_name, name=name,
                provider=provider

            )
            for instance in instances_list:
                asset_id = md5(instance.get('InstanceId').encode('utf-8'))\
                    .hexdigest()
                hostname = instance.get('HostName', None)
                platform = instance.get('OSType', None)
                public_ip = instance.get('PublicIpAddress', None)\
                    .get('IpAddress', None)[0]
                port = 3389 if platform == 'windows' else 22
                is_active = False

                try:
                    defaults = {
                        'hostname': hostname, 'platform': platform,
                        'is_active': is_active, 'ip': public_ip, 'port': port,
                    }
                    asset = Asset.objects.update_or_create(
                        defaults=defaults, id=asset_id
                    )[0]
                    asset.nodes.add(node)
                    asset.save()
                except Exception as e:
                    logger.error(e)
                    return False
        return True

    @staticmethod
    def get_cloud_info(name):
        regions = (
            {'cn-qingdao': '华北 1 (青岛)',
             'cn-beijing': '华北 2 (北京)',
             'cn-zhangjiakou': '华北 3 (张家口)',
             'cn-huhehaote': '华北 5 (呼和浩特)',
             'cn-hangzhou': '华东 1 (杭州)',
             'cn-shanghai': '华东 2 (上海)',
             'cn-shenzhen': '华南 1 (深圳)',
             'cn-hongkong': '香港',
             'ap-southeast-1': '亚太东南 1 (新加坡)',
             'ap-southeast-2': '亚太东南 2 (悉尼)',
             'ap-southeast-3': '亚太东南 3 (吉隆坡)',
             'ap-southeast-5': '亚太东南 5 (雅加达)',
             'ap-south-1': '亚太南部 1 (孟买)',
             'ap-northeast-1': '亚太东北 1 (东京)',
             'us-west-1': '美国西部 1 (硅谷)',
             'us-east-1': '美国东部 1 (弗吉尼亚)',
             'eu-central-1': '欧洲中部 1 (法兰克福)',
             'me-east-1': '中东东部 1 (迪拜)'}
        )
        cloud_info = CloudSettingForm.get_info_by_name(name)
        cloud_info.update({'regions': regions})
        return cloud_info
