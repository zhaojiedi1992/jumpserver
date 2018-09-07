import logging
import stat
from django.http.response import FileResponse

from .base import BaseVolume


logger = logging.getLogger(__name__)


class SFTPVolume(BaseVolume):
    def __init__(self, sftp):
        self.sftp = sftp
        self.root_name = 'Home'
        super().__init__()
        self._stat_cache = {}

    def get_volume_id(self):
        volume_id = '{}'.format(id(self.sftp))
        return self._degest(volume_id)

    def info(self, target):
        if target == '':
            remote_path = self.base_path
        else:
            remote_path = self._get_remote_path_from_hash(target)
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
            "hash": self._hash(remote_path),
            "phash": self._hash(_parent_path),
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

    def get_list(self, target, include_self=True):
        if target in ['', '/']:
            remote_path = self.base_path
        else:
            remote_path = self._get_remote_path_from_hash(target)
        return self._get_list(remote_path, include_self=include_self)

    def _get_list(self, remote_path, include_self=True):
        """ Returns current dir dirs/files
        """
        files = []
        if include_self:
            files.append(self._get_stat_info(remote_path))
        children_attrs = self.sftp.listdir_attr(remote_path)
        for attr in children_attrs:
            item_path = self._join(remote_path, attr.filename)
            info = self._get_stat_info(item_path, attr=attr)
            files.append(info)
        return files

    def list(self, target):
        """ Returns a list of files/directories in the target directory. """
        files = []
        for info in self._get_list(target):
            files.append(info['name'])
        return files

    def tree(self, target):
        """ Get the sub directory of directory
        """
        tree = []
        infos = self._get_list(target)
        for info in infos:
            if info['mime'] == 'directory':
                tree.append(info)
        return tree

    def parents(self, target, deep=0):
        parents = []
        if target in ['/', '']:
            _path = '/'
        else:
            _path = self._get_path_from_hash(target)
        __path = _path.strip(self.path_sep).split(self.path_sep)
        if deep == 0 or deep > len(__path) - 1:
            deep = len(__path) or 1  #  或许只查询 '/' 的
        for i in range(deep):
            __path.pop()
            parent_path = '/' + self.path_sep.join(__path)
            remote_path = self._join(self.base_path, parent_path)
            infos = self._get_list(remote_path)
            for info in infos:
                if info['mime'] == 'directory':
                    parents.append(info)
        return parents

    def read_file_view(self, request, target, download=True):
        remote_path = self._get_remote_path_from_hash(target)
        f = self.sftp.open(remote_path, 'r')
        response = FileResponse(f)
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment;filename="{}"'\
            .format(self._base_name(remote_path))
        return response

    def mkdir(self, names, parent, many=False):
        """ Creates a new directory. """
        parent_path = self._get_remote_path_from_hash(parent)
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
        parent_path = self._get_remote_path_from_hash(parent)
        remote_path = self._join(parent_path, name)
        with self.sftp.open(remote_path, mode='w'):
            pass
        return self._get_stat_info(remote_path)

    def rename(self, name, target):
        """ Renames a file or directory. """
        remote_path = self._get_remote_path_from_hash(target)
        new_remote_path = self._join(self._parent_path(remote_path), name)
        self.sftp.rename(remote_path, new_remote_path)
        return {
            'added': [self._get_stat_info(new_remote_path)],
            'removed': [target]
        }

    def paste(self, targets, source, dest, cut):
        """ Moves/copies target files/directories from source to dest. """
        return {"error": "Not support paste"}

    def remove(self, target):
        """ Delete a File or Directory object. """
        remote_path = self._get_remote_path_from_hash(target)
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
        remote_path = self._get_remote_path_from_hash(parent)
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
        info = self.info(target)
        return info.get('size') or 'Unknown'

