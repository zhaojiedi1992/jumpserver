import logging
import paramiko
import traceback
import stat
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.shortcuts import render_to_response
from django.template import RequestContext
import os

from .base import BaseVolume
from .. import models


logger = logging.getLogger(__name__)


class SFTPVolume(BaseVolume):
    def __init__(self, host='127.0.0.1', port=22, username='root',
                 password=None, pkey=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.pkey = pkey
        self._ssh = None
        self.root_name = 'Home'
        super().__init__()
        self._stat_cache = {}

    def _connect(self):
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self._ssh.connect('192.168.244.140', username='root',
                              password='redhat')
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

    def get_volume_id(self):
        volume_id = '{}@{}@{}'.format(self.host, self.port, self.username)
        return self._hash(volume_id)

    def get_info(self, target):
        if target == '':
            remote_path = os.path.join(self.base_path, '/')
        else:
            remote_path = self.get_remote_path_by_hash(target)
        attr = self.sftp.lstat(remote_path)
        if remote_path in ['', '/']:
            attr.filename = self.root_name
        else:
            attr.filename = self._base_name(remote_path)
        return self._get_stat_info(attr, remote_path)

    def _base_name(self, remote_path):
        return os.path.basename(remote_path)

    def _parent_path(self, remote_path):
        if remote_path != '/':
            remote_path = remote_path.rstrip('/')
        parent_path = os.path.dirname(remote_path)
        return parent_path

    def _get_stat_info(self, attr, remote_path):
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

        if remote_path in ['', '/']:
            del data['phash']
            data['locked'] = 1
            data['volume_id'] = self.get_volume_id()
            data['name'] = self.root_name
        return data

    def _get_list(self, target):
        print("list: {}".format(target))
        files = []
        if target in ['', '/']:
            remote_path = os.path.join(self.base_path, '/')
        else:
            remote_path = self.get_remote_path_by_hash(target)

        attrs = self.sftp.listdir_attr(remote_path)
        for attr in attrs:
            item_path = os.path.join(remote_path, attr.filename)
            info = self._get_stat_info(attr, item_path)
            files.append(info)
        return files

    def get_tree(self, target, ancestors=False, siblings=False):
        """ Returns a list of dicts describing children/ancestors/siblings of
            the target directory.

            Siblings of the root node are always excluded, as they refer to
            root directories of other file collections.
        """
        print("Get tree")
        tree = []
        files = self._get_list(target)
        tree += files

        # Add ancestors next, if required
        if ancestors:
            tree.append(self.get_info(target))
            if target in ['', '/']:
                remote_path = os.path.join(self.base_path, '/')
                return tree
            else:
                remote_path = self.get_remote_path_by_hash(target)
            paths = remote_path.split('/')
            for i in range(len(paths)):
                paths.pop()
                ancestor_path = '/'.join(paths)
                if ancestor_path == self.base_path:
                    break
                files = self._get_list(self.get_hash(ancestor_path))
                for f in files:
                    if f['mime'] == 'directory':
                        tree.append(f)
        return tree

    def _create_object(self, name, parent_hash, model):
        """ Helper function to create objects (files/directories).
        """

        parent = self.get_object(parent_hash)

        new_obj = model(name=name,
                        parent=parent,
                        collection=self.collection)
        try:
            new_obj.validate_unique()
        except ValidationError as e:
            logger.exception(e)
            raise Exception("\n".join(e.messages))

        new_obj.save()
        return new_obj.get_info()

    def read_file_view(self, request, hash):
        file = self.get_object(hash)
        return render_to_response('filemanager/read_file.html',
                                  {'file': file},
                                  RequestContext(request))

    def mkdir(self, name, parent):
        """ Creates a new directory. """
        return self._create_object(name, parent, self.directory_model)

    def mkfile(self, name, parent):
        """ Creates a new file. """
        return self._create_object(name, parent, self.file_model)

    def rename(self, name, target):
        """ Renames a file or directory. """
        object = self.get_object(target)
        object.name = name
        object.save()
        return {'added': [object.get_info()],
                'removed': [target]}

    def list(self, target):
        """ Returns a list of files/directories in the target directory. """
        list = []
        for object in self.get_tree(target):
            list.append(object['name'])
        return list

    def paste(self, targets, source, dest, cut):
        """ Moves/copies target files/directories from source to dest. """
        source_dir = self.get_object(source)
        dest_dir = self.get_object(dest)
        added = []
        removed = []
        for target in targets:
            object = self.get_object(target)
            object.parent = dest_dir
            if not cut:
                # This is a copy so the original object should not be changed.
                # Setting the id to None causes Django to insert a new model
                # instead of updating the existing one.
                object.id = None

            # If an object with the same name already exists in the target
            # directory, it should be deleted. This needs to be done for
            # both Files and Directories. Using filter() and iterating
            # over the results is a bit cleaner than using get() and checking
            # if an object was returned, even though most of the time both
            # querysets will be empty.
            dirs = self.directory_model.objects.filter(name=object.name,
                                                   parent=object.parent)
            files = self.file_model.objects.filter(name=object.name,
                                                  parent=object.parent)
            for dir in dirs:
                removed.append(dir.get_hash())
                dir.delete()
            for file in files:
                removed.append(file.get_hash())
                file.delete()

            object.save()
            added.append(object.get_info())
            if cut:
                removed.append(object.get_info()['hash'])

        return {'added': added,
                'removed': removed}

    def remove(self, target):
        """ Delete a File or Directory object. """
        object = self.get_object(target)
        object.delete()
        return target

    def upload(self, files, parent):
        """ For now, this uses a very naive way of storing files - the entire
            file is read in to the File model's content field in one go.

            This should be updated to use read_chunks to add the file one 
            chunk at a time.
        """
        added = []
        parent = self.get_object(parent)
        for upload in files.getlist('upload[]'):
            new_file = self.file_model(name=upload.name,
                                       parent=parent,
                                       collection=self.collection,
                                       content=upload.read())
            try:
                new_file.validate_unique()
            except ValidationError as e:
                logger.exception(e)
                raise Exception("\n".join(e.messages))

            new_file.save()
            added.append(new_file.get_info())
        return {'added': added}
