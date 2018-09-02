# -*- coding: utf-8 -*-
#
import os
from datetime import datetime
import paramiko
import traceback
import stat
import hashlib

from django.utils.six import BytesIO
from urllib.parse import urlparse
from django.core.files.base import File

from common.utils import get_logger
from .base import BaseVolume

logger = get_logger(__file__)


class SFTPVolume(BaseVolume):

    def __init__(self, host=None, port=22, username='root',
                 password=None, pkey=None, base_path='/'):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.pkey = pkey
        self.base_path = base_path
        self._dir_mode = '0o755'
        self._file_mode = '0o644'
        self._ssh = None
        super().__init__()

    def get_volume_id(self):
        return 'fc%s' % '123'

    def _connect(self):
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self._ssh.connect('192.168.244.140', username='root', password='redhat')
            # self._ssh.connect(self.host, port=self.port, username=self.username,
            #                   password=self.password, pkey=self.pkey, timeout=30)
        except paramiko.AuthenticationException as e:
            logger.error(e)
            raise paramiko.AuthenticationException(e)
        except Exception as e:
            logger.error(traceback.print_exc())
            raise paramiko.AuthenticationException(e)
        if not hasattr(self, '_sftp'):
            self._sftp = self._ssh.open_sftp()

    @property
    def sftp(self):
        """Lazy SFTP connection"""
        if not hasattr(self, '_sftp'):
            self._connect()
        return self._sftp

    def stat(self, target):
        path = self._remote_path(target)
        attr = self.sftp.stat(path)
        data = {
            "name": target,
            "hash": self.__hash(path),
            "mime": "directory" if stat.S_ISDIR(attr.st_mode) else "file",
            "read": 1,
            "write": 1,
            "size": 0,
        }
        return data

    def get_tree(self, target, ancestors=False, siblings=False):
        tree = []
        remote_path = self._remote_path(target)
        dirs, files, types = self.list(remote_path)




    def __hash(self, path):
        """Hash of the path"""
        m = hashlib.md5()
        m.update(path)
        return str(m.hexdigest())

    def _join(self, *args):
        # Use the path module for the remote host type to join a path together
        return os.path.join(*args)

    def _remote_path(self, name):
        return self._join(self.base_path, name)

    def _open(self, name, mode='rb'):
        return SFTPStorageFile(name, self, mode)

    def _read(self, name):
        remote_path = self._remote_path(name)
        return self.sftp.open(remote_path, 'rb')

    def _chown(self, path, uid=None, gid=None):
        """Set uid and/or gid for file at path."""
        # Paramiko's chown requires both uid and gid, so look them up first if
        # we're only supposed to set one.
        if uid is None or gid is None:
            attr = self.sftp.stat(path)
            uid = uid or attr.st_uid
            gid = gid or attr.st_gid
        self.sftp.chown(path, uid, gid)

    def _mkdir(self, path):
        """Create directory, recursing up to create parent dirs if
        necessary."""
        parent = os.path.dirname(path)
        if not self.exists(parent):
            self._mkdir(parent)
        self.sftp.mkdir(path)

        if self._dir_mode is not None:
            self.sftp.chmod(path, self._dir_mode)

        # if self._uid or self._gid:
        #     self._chown(path, uid=self._uid, gid=self._gid)

    def _save(self, name, content, **kwargs):
        """Save file via SFTP."""
        content.open()
        path = self._remote_path(name)
        dirname = os.path.dirname(path)
        if not self.exists(dirname):
            self._mkdir(dirname)
        if 'mode' in kwargs and 'a' in kwargs['mode']:
            f = self.sftp.open(path, 'ab')
        else:
            f = self.sftp.open(path, 'wb')
        f.write(content.file.read())
        f.close()

        # set file permissions if configured
        if self._file_mode is not None:
            self.sftp.chmod(path, self._file_mode)
        return name

    def delete(self, name):
        remote_path = self._remote_path(name)
        self.sftp.remove(remote_path)

    def delete_dir(self, name):
        remote_path = self._remote_path(name)
        self.sftp.rmdir(remote_path)

    def exists(self, name):
        # Try to retrieve file info.  Return true on success, false on failure.
        remote_path = self._remote_path(name)

        try:
            self.sftp.stat(remote_path)
            return True
        except IOError:
            return False

    def _isdir_attr(self, item):
        # Return whether an item in sftp.listdir_attr results is a directory
        if item.st_mode is not None:
            return stat.S_IFMT(item.st_mode) == stat.S_IFDIR
        else:
            return False

    def listdir(self, path):
        remote_path = self._remote_path(path)
        dirs, files, files_type = [], [], {}
        for item in self.sftp.listdir_attr(remote_path):
            if self._isdir_attr(item):
                dirs.append(item.filename)
            else:
                files.append(item.filename)
                files_type[item.filename] = str(item)[0:1]
        return dirs, files, files_type

    def size(self, name):
        remote_path = self._remote_path(name)
        return self.sftp.stat(remote_path).st_size

    def accessed_time(self, name):
        remote_path = self._remote_path(name)
        utime = self.sftp.stat(remote_path).st_atime
        return datetime.fromtimestamp(utime)

    def modified_time(self, name):
        remote_path = self._remote_path(name)
        utime = self.sftp.stat(remote_path).st_mtime
        return datetime.fromtimestamp(utime)

    def url(self, name):
        if self._base_url is None:
            raise ValueError("This file is not accessible via a URL.")
        return urlparse.urljoin(self._base_url, name).replace('\\', '/')


class SFTPStorageFile(File):
    def __init__(self, name, storage, mode):
        self._name = name
        self._storage = storage
        self._mode = mode
        self._is_dirty = False
        self.file = BytesIO()
        self._is_read = False

    @property
    def name(self):
        return self._name

    @property
    def size(self):
        if not hasattr(self, '_size'):
            self._size = self._storage.size(self._name)
        return self._size

    def read(self, num_bytes=None):
        if not self._is_read:
            self.file = self._storage._read(self._name)
            self._is_read = True

        return self.file.read(num_bytes)

    def write(self, content):
        if 'w' not in self._mode and 'a' not in self._mode:
            raise AttributeError("File was opened for read-only access.")
        self.file = BytesIO(content)
        self._is_dirty = True
        self._is_read = True

    def close(self):
        if self._is_dirty:
            self._storage._save(self._name, self, mode=self._mode)
        self.file.close()