import base64
import os
import hashlib
import logging

logger = logging.getLogger(__name__)


class BaseVolume:
    def __init__(self, *args, **kwargs):
        self.base_path = '/'
        self.path_sep = '/'
        self.dir_mode = '0o755'
        self.file_mode = '0o644'
    #
    # @classmethod
    # def get_volume(cls, request):
    #     raise NotImplementedError

    def get_volume_id(self):
        """ Returns the volume ID for the volume, which is used as a prefix
            for client hashes.
        """
        raise NotImplementedError

    def _get_path_from_hash(self, _hash):
        """
        通过_hash获取path
        :param _hash:
        :return:
        """
        volume_id, path = self._get_volume_id_and_path_from_hash(_hash)
        if volume_id != self.get_volume_id():
            return ''
        return path

    def _get_remote_path_from_hash(self, _hash):
        path = self._get_path_from_hash(_hash)
        if self.base_path:
            return os.path.join(self.base_path, path)
        return path

    def _hash(self, path):
        """
        通过path生成hash
        :param path:
        :return:
        """
        _hash = "{}_{}".format(
            self.get_volume_id(),
            self._encode(path)
        )
        return _hash

    def _degest(self, s):
        m = hashlib.md5()
        m.update(s.encode())
        return str(m.hexdigest())

    @classmethod
    def _get_volume_id_and_path_from_hash(cls, _hash):
        volume_id, _path = _hash.split('_', 1)
        return volume_id, cls._decode(_path)

    @staticmethod
    def _encode(content):
        if isinstance(content, str):
            content = content.encode()
        _hash = base64.b64encode(content).decode()
        _hash = _hash.translate(str.maketrans('+=/', '-_.'))
        return _hash

    @staticmethod
    def _decode(_hash):
        _hash = _hash.translate(str.maketrans('-_.', '+=/'))
        if isinstance(_hash, str):
            _hash = _hash.encode()
        _hash = base64.b64decode(_hash).decode()
        return _hash

    def _base_name(self, remote_path):
        return os.path.basename(remote_path)

    def _parent_path(self, remote_path):
        if remote_path != '/':
            remote_path = remote_path.rstrip('/')
        parent_path = os.path.dirname(remote_path)
        return parent_path

    def _join(self, *args):
        return os.path.join(*args)

    def read_file_view(self, request, target):
        """ Django view function, used to display files in response to the
            'file' command.

            :param request: The original HTTP request.
            :param target: The hash of the target file.
            :returns: dict -- a dict describing the new directory.
        """
        raise NotImplementedError

    def info(self, target):
        """ Returns a dict containing information about the target directory
            or file. This data is used in response to 'open' commands to
            populates the 'cwd' response var.

            :param target: The hash of the directory for which we want info.
            If this is '', return information about the root directory.
            :returns: dict -- A dict describing the directory.
        """
        raise NotImplementedError

    def mkdir(self, name, parent):
        """ Creates a directory.

            :param name: The name of the new directory.
            :param parent: The hash of the parent directory.
            :returns: dict -- a dict describing the new directory.
        """
        raise NotImplementedError

    def mkfile(self, name, parent):
        """ Creates a directory.

            :param name: The name of the new file.
            :param parent: The hash of the parent directory.
            :returns: dict -- a dict describing the new file.
        """
        raise NotImplementedError

    def rename(self, name, target):
        """ Renames a file or directory.

            :param name: The new name of the file/directory.
            :param target: The hash of the target file/directory.
            :returns: dict -- a dict describing which objects were added and
            removed.
        """
        raise NotImplementedError

    def list(self, target):
        """ Lists the contents of a directory.

            :param target: The hash of the target directory.
            :returns: list -- a list containing the names of files/directories
            in this directory.
        """
        raise NotImplementedError

    def tree(self, target):
        """ Get the sub directory of directory

        :param target: The hash of the target directory.
        :return: list - a list of containing the names of sub directories
        """
        raise NotImplementedError

    def parents(self, target, deep=0):
        """ Returns all parent folders and its sub directory on required deep
            This command is invoked when a directory is reloaded in the client.
            Data provided by 'parents' command should enable the correct drawing
            of tree hierarchy directories.
        :param target: The hash of the target directory.
        :param deep: The deep to show
        :return list - a list of containing parent and sub directory info
        """
        raise NotImplementedError

    def paste(self, targets, source, dest, cut):
        """ Moves/copies target files/directories from source to dest.

            If a file with the same name already exists in the dest directory
            it should be overwritten (the client asks the user to confirm this
            before sending the request).

            :param targets: A list of hashes of files/dirs to move/copy.
            :param source: The current parent of the targets.
            :param dest: The new parent of the targets.
            :param cut: Boolean. If true, move the targets. If false, copy the
            targets.
            :returns: dict -- a dict describing which targets were moved/copied.
        """
        raise Exception("Not support paste")

    def remove(self, targets):
        """ Deletes the target files/directories.

            The 'rm' command takes a list of targets - this function is called
            for each target, so should only delete one file/directory.

            :param targets: A list of hashes of files/dirs to delete.
            :returns: string -- the hash of the file/dir that was deleted.
        """
        raise NotImplementedError

    def upload(self, files, parent):
        """ Uploads one or more files in to the parent directory.

            :param files: A list of uploaded file objects, as described here:
            https://docs.djangoproject.com/en/dev/topics/http/file-uploads/
            :param parent: The hash of the directory in which to create the
            new files.
            :returns: TODO
        """
        raise NotImplementedError
    #
    # def _hash(self, s):
    #     m = hashlib.md5()
    #     m.update(s._encode())
    #     return str(m.hexdigest())
