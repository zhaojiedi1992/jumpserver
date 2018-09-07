import json
import uuid
import os

import paramiko
import socket
import time
import threading

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.shortcuts import render_to_response
from django.views.generic import TemplateView, View
from django.template import RequestContext

from .forms import SFTPLoginForm
from .volumes import SFTPVolume
from .connector import ElFinderConnector


class JmsWebSFTPView:
    pass


class DefaultConnectionProxy:
    """
    Proxy for accessing the default DatabaseWrapper object's attributes. If you
    need to access the DatabaseWrapper object itself, use
    connections[DEFAULT_DB_ALIAS] instead.
    """
    # def __getattr__(self, item):
    #     return getattr(connections[DEFAULT_DB_ALIAS], item)
    #
    # def __setattr__(self, name, value):
    #     return setattr(connections[DEFAULT_DB_ALIAS], name, value)
    #
    # def __delattr__(self, name):
    #     return delattr(connections[DEFAULT_DB_ALIAS], name)
    #
    # def __eq__(self, other):
    #     return connections[DEFAULT_DB_ALIAS] == other

from django.db import connection


class SFTPConnectionManager:
    _connections = {}
    _sftp = {}

    @classmethod
    def new_sftp_client(cls, host, port=22, username='', **kwargs):
        cache_key = '{}_{}_{}'.format(host, port, username)
        cache_ssh = cls._connections.get(cache_key)

        if cache_ssh and not cache_ssh.closed:
            ssh = cache_ssh
        else:
            ssh, error = cls.connect(
                host=host, port=port, username=username, timeout=5,
                auth_timeout=5, **kwargs
            )
            if ssh is None:
                return None, error
            cls._connections[cache_key] = ssh
        token = str(uuid.uuid4())
        try:
            sftp = ssh.open_sftp()
            sftp.last_seen = time.time()
            cls._sftp[token] = sftp
            return token, None
        except Exception as e:
            return None, e

    @classmethod
    def connect(cls, host, **kwargs):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            print(kwargs)
            ssh.connect(host, **kwargs)
            return ssh, None
        except paramiko.AuthenticationException as e:
            return None, e
        except socket.timeout:
            host = kwargs.get('host')
            port = kwargs.get('port', 22)
            return None, "Connection {}:{} timeout".format(host, port)
        except Exception as e:
            return None, "Unknown error {}".format(e)

    @classmethod
    def get_sftp_client(cls, token):
        sftp = cls._sftp.get(token)
        if not sftp:
            return None, 'Connection expired'
        elif sftp.get_channel().closed:
            del cls._sftp[token]
            return None, 'Connection closed'
        sftp.last_seen = time.time()
        return sftp, None


class CommonSFTPView(View):
    form_class = SFTPLoginForm
    template = 'filemanager/common_sftp.html'

    def get(self, request):
        form = self.form_class()
        return render(request, self.template, context={'form': form})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            token, error = SFTPConnectionManager.new_sftp_client(
                host=form.cleaned_data['host'], port=form.cleaned_data['port'],
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password']
            )
            if not token:
                form.add_error('host', error)
            else:
                return redirect('filemanager:sftp-filermanager-view', token=token)
        return render(request, self.template, context={'form': form})


class SFTPManagerView(TemplateView):
    template_name = 'filemanager/file_manager.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'token': self.kwargs.get('token')
        })
        return context


class SFTPConnectorView(View):
    def get(self, request, *args, **kwargs):
        # coll_id = self.kwargs.get('coll_id')
        token = kwargs.get('token')
        sftp, error = SFTPConnectionManager.get_sftp_client(token)
        if sftp is None:
            return JsonResponse({"error": str(error)})

        volume = SFTPVolume(sftp)
        # volume = ModelVolume(coll_id=coll_id)
        finder = ElFinderConnector([volume])
        finder.run(request)

        # Some commands (e.g. read file) will return a Django View - if it
        # is set, return it directly instead of building a response
        if finder.return_view:
            return finder.return_view

        response = HttpResponse(
            content_type=finder.headers['Content-type'],
            status=finder.status_code
        )
        if finder.headers['Content-type'] == 'application/json':
            response.content = json.dumps(finder.response)
        else:
            response.content = finder.response
        return response

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


def read_file(request, volume, file_hash, template="read_file.html"):
    """ Default view for responding to "open file" requests.

        coll: FileCollection this File belongs to
        file: The requested File object
    """
    return render_to_response(template,
                              {'file': file_hash},
                              RequestContext(request))