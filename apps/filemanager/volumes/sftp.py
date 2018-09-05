import logging
import paramiko
import traceback
import stat
import os
from django.core.exceptions import ValidationError
from django.http.response import FileResponse

from .base import BaseVolume


logger = logging.getLogger(__name__)


class SFTPVolume(BaseVolume):
    _sftp_cache = {}

    def __init__(self, host='127.0.0.1', port=22, username='root',
                 password=None, pkey=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.pkey = pkey
        self._ssh = None
        self._sftp = None
        self.root_name = 'Home'
        super().__init__()
        self._stat_cache = {}

    def _connect(self):
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self._ssh.connect('localhost', port=2223, username='admin',
                              password='admin')
            # self._ssh.connect('192.168.244.177', username='root', password='redhat123')
            # self._ssh.connect(self.host, port=self.port, username=self.username,
            #                   password=self.password, pkey=self.pkey, timeout=30)
        except paramiko.AuthenticationException as e:
            logger.error(e)
            raise paramiko.AuthenticationException(e)
        except Exception as e:
            logger.error(traceback.print_exc())
            raise paramiko.AuthenticationException(e)
        if self._sftp is None:
            self._sftp = self._ssh.open_sftp()

    @property
    def sftp(self):
        cached = self._sftp_cache.get(self.host)
        if cached is not None:
            return cached
        if self._sftp is None:
            self._connect()
        if self._sftp is not None:
            self._sftp_cache[self.host] = self._sftp
        return self._sftp

    def get_volume_id(self):
        volume_id = '{}@{}@{}'.format(self.host, self.port, self.username)
        return self._hash(volume_id)

    def get_info(self, target):
        if target == '':
            remote_path = self.base_path
        else:
            remote_path = self.get_remote_path_by_hash(target)
        return self._get_stat_info(remote_path)

    def _get_stat_info(self, remote_path, attr=None):
        if attr is None:
            attr = self.sftp.lstat(remote_path)
        if not hasattr(attr, 'filename'):
            if remote_path == self.base_path:
                filename = self.root_name
            else:
                filename = self._base_name(remote_path)
            attr.filename = filename
        _parent_path = self._parent_path(remote_path)

        data = {
            "name": attr.filename,
            "hash": self.get_hash(remote_path),
            "phash": self.get_hash(_parent_path),
            "ts": attr.st_mtime,
            "size": attr.st_size,
            "mime": "directory" if stat.S_ISDIR(attr.st_mode) else "file",
            "read": 1,
            "write": 1,
        }
        if data["mime"] == 'directory':
            data["dirs"] = 1

        if remote_path == self.base_path:
            del data['phash']
            data['locked'] = 1
            data['volume_id'] = self.get_volume_id()
            data['name'] = self.root_name
        return data

    def _get_list(self, target, include_self=True):
        """ Returns current dir dirs/files
        """
        files = []
        if target in ['', '/']:
            remote_path = self.base_path
        else:
            remote_path = self.get_remote_path_by_hash(target)
        if include_self:
            files.append(self.get_info(target))
        children_attrs = self.sftp.listdir_attr(remote_path)
        for attr in children_attrs:
            item_path = self._join(remote_path, attr.filename)
            info = self._get_stat_info(item_path, attr=attr)
            files.append(info)
        return files

    def get_tree(self, target, ancestors=False, siblings=False):
        """ Returns a list of dicts describing children/ancestors/siblings of
            the target directory.

            Siblings of the root node are always excluded, as they refer to
            root directories of other file collections.
        """
        tree = []
        files = self._get_list(target)
        tree += files

        # Add ancestors next, if required
        if ancestors:
            tree.append(self.get_info(target))
            if target in ['', '/']:
                return tree
            remote_path = self.get_remote_path_by_hash(target)
            paths = remote_path.split('/')
            for i in range(len(paths)):
                paths.pop()
                ancestor_path = '/'.join(paths)
                if ancestor_path == '':
                    ancestor_path = '/'
                files = self._get_list(self.get_hash(ancestor_path))
                for f in files:
                    if f['mime'] == 'directory':
                        tree.append(f)
                if ancestor_path == self.base_path:
                    break
        return tree

    def read_file_view(self, request, target, download=True):
        remote_path = self.get_remote_path_by_hash(target)
        f = self.sftp.open(remote_path, 'r')
        response = FileResponse(f)
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment;filename="{}"'\
            .format(self._base_name(remote_path))
        return response

    def mkdir(self, names, parent, many=False):
        """ Creates a new directory. """
        parent_path = self.get_remote_path_by_hash(parent)
        data = []
        if not many:
            names = [names]
        for name in names:
            remote_path = self._join(parent_path, name.lstrip('/'))
            self.sftp.mkdir(remote_path)
            data.append(self._get_stat_info(remote_path))
        return data

    def mkfile(self, name, parent):
        """ Creates a new file. """
        parent_path = self.get_remote_path_by_hash(parent)
        remote_path = self._join(parent_path, name)
        with self.sftp.open(remote_path, mode='w'):
            pass
        return self._get_stat_info(remote_path)

    def rename(self, name, target):
        """ Renames a file or directory. """
        remote_path = self.get_remote_path_by_hash(target)
        new_remote_path = self._join(self._parent_path(remote_path), name)
        self.sftp.rename(remote_path, new_remote_path)
        return {
            'added': [self._get_stat_info(new_remote_path)],
            'removed': [target]
        }

    def list(self, target):
        """ Returns a list of files/directories in the target directory. """
        files = []
        for info in self.get_tree(target):
            files.append(info['name'])
        return files

    def paste(self, targets, source, dest, cut):
        """ Moves/copies target files/directories from source to dest. """
        return {"error": "Not support paste"}

    def remove(self, target):
        """ Delete a File or Directory object. """
        remote_path = self.get_remote_path_by_hash(target)
        try:
            self.sftp.unlink(remote_path)
        except OSError:
            raise OSError("Delete {} failed".format(self._base_name(remote_path)))
        return target

    def upload(self, files, parent):
        """ For now, this uses a very naive way of storing files - the entire
            file is read in to the File model's content field in one go.

            This should be updated to use read_chunks to add the file one 
            chunk at a time.
        """
        added = []
        remote_path = self.get_remote_path_by_hash(parent)
        item = files.get('upload[]')
        item_path = self._join(remote_path, item.name)
        try:
            self.sftp.stat(item_path)
            raise Exception("File {} exist".format(item.name))
        except OSError:
            pass
        with self.sftp.open(item_path, 'w') as rf:
            for chunk in item.chunks():
                rf.write(chunk)
        added.append(self._get_stat_info(item_path))
        return {'added': added}

    def size(self, target):
        info = self.get_info(target)
        return info.get('size') or 'Unknown'
