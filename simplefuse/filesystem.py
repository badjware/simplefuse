import os
import sys

from time import time
from stat import S_IFDIR, S_IFLNK, S_IFREG
from errno import EPERM, ENOENT, ENODATA
from fuse import FUSE, FuseOSError, Operations

# ENOATTR is missing from python errno, so we use ENODATA instead
ENOATTR = ENODATA

class Node:
    def __init__(self, name):
        now = time()

        self.name = name

        attr = dict()
        attr['st_mode'] = 0o655 | S_IFREG
        attr['st_uid'] = os.getuid()
        attr['st_gid'] = os.getgid()
        attr['st_nlink'] = 1
        attr['st_size'] = 0
        attr['st_ctime'] = now
        attr['st_mtime'] = now
        attr['st_atime'] = now
        self.attr = attr

    def chown(self, uid, gid):
        self.attr['st_uid'] = uid
        self.attr['st_gid'] = gid

    def __str__(self):
        return self.name


class Directory(Node):
    def __init__(self, name):
        super().__init__(name)
        self.attr['st_mode'] = (0o755 | S_IFDIR)
        self.children = dict()

    def get_child(self, name):
        return self.children[name]

    def add_child(self, name, node):
        self.children[name] = node

    def remove_child(self, name):
        try:
            node = self.children[name]
            del self.children[name]
            return node
        except KeyError:
            raise FuseOSError(ENOENT)

    def chmod(self, mode):
        self.attr['st_mode'] = mode | S_IFDIR

    def create(self, name, mode):
        node = File(name)
        node.attr['st_mode'] = mode | S_IFREG
        self.add_child(name, node)

    def mkdir(self, name, mode):
        node = Directory(name)
        self.attr['st_mode'] = mode | S_IFDIR
        self.add_child(name, node)

        self.attr['st_nlink'] += 1

    def rmdir(self, name):
        self.remove_child(name)

        self.attr['st_nlink'] -= 1

    def symlink(self, name, target):
        node = Symlink(name, target)
        self.add_child(name, node)

    def unlink(self, name):
        self.remove_child(name)


class File(Node):
    def __init__(self, name):
        super().__init__(name)
        self.attr['st_mode'] = (0o755 | S_IFREG)
        self.content = b''

    def chmod(self, mode):
        self.attr['st_mode'] = mode | S_IFREG

    def read(self, length, offset):
        return self.content[offset:offset+length]

    def write(self, buffer, offset):
        self.content = self.content[:offset] + buffer
        self.attr['st_size'] = len(self.content)

    def truncate(self, length):
        self.content = self.content[:length]


class Symlink(Node):
    def __init__(self, name, target):
        super().__init__(name)
        self.attr['st_mode'] = (0o755 | S_IFLNK)
        self.target = target


class Filesystem(Operations):
    def __init__(self, root_node=Directory('/')):
        self.root_node = root_node
        self.fd = 0

    def mount(self, mount_point):
        return FUSE(self, mount_point, foreground=True)

    def chmod(self, path, mode):
        node = self._get_node(path)
        node.chmod(mode)
        return 0

    def chown(self, path, uid, gid):
        node = self._get_node(path)
        node.chown(uid, gid)

    def create(self, path, mode):
        parent_path, name = os.path.split(path)
        node = self._get_node(parent_path)
        node.create(name, mode)

        self.fd += 1
        return self.fd

    def getattr(self, path, handler=None):
        node = self._get_node(path)
        return node.attr

    def getxattr(self, path, name, position=0):
        node = self._get_node(path)
        try:
            return node.attr[name]
        except KeyError:
            raise FuseOSError(ENOATTR)

    def listxattr(self, path):
        node = self._get_node(path)
        return node.attr.keys()

    def mkdir(self, path, mode):
        parent_path, name = os.path.split(path)
        node = self._get_node(parent_path)
        node.mkdir(name, mode)

    def open(self, path, flags):
        node = self._get_node(path)
        self.fd += 1
        return self.fd

    def read(self, path, size, offset, handler):
        node = self._get_node(path)
        return node.read(size, offset)

    def readdir(self, path, handler):
        node = self._get_node(path)
        yield '.'
        yield '..'
        for dir in node.children.keys():
            yield dir

    def readlink(self, path):
        node = self._get_node(path)
        return node.target

    def removexattr(self, path, name):
        node = self._get_node(path)
        try:
            del node.attr[name]
        except KeyError:
            raise FuseOSError(ENOATTR)

    def rename(self, old, new):
        old_parent_path, old_name = os.path.split(old)
        new_parent_path, new_name = os.path.split(new)
        old_parent_node = self._get_node(old_parent_path)
        new_parent_node = self._get_node(new_parent_path)

        node = old_parent_node.remove_child(old_name) 
        new_parent_node.add_child(new_name, node)

    def rmdir(self, path):
        parent_path, name = os.path.split(path)
        node = self._get_node(parent_path)
        node.rmdir(name)

    def setxattr(self, path, name, value, options, position=0):
        node = self._get_node(path)
        node.attr[name] = value

    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    def symlink(self, source, target):
        parent_path, name = os.path.split(source)
        node = self._get_node(parent_path)
        node.symlink(name, target)

    def truncate(self, path, length, fh=None):
        node = self._get_node(path)
        node.truncate(length)

    def unlink(self, path):
        parent_path, name = os.path.split(path)
        node = self._get_node(parent_path)
        node.unlink(name)

    def utimes(self, path, times=None):
        node = self._get_node(path)
        now = time()
        atime, mtime = times if times else (now, now)

        node.attr['st_atime'] = atime
        node.attr['st_mtime'] = mtime

    def write(self, path, buffer, offset, fh):
        node = self._get_node(path)
        node.write(buffer, offset)
        return len(buffer)

    def _get_node(self, path):
        node = self.root_node
        try:
            for name in path.split(os.sep):
                if name != '':
                    node = node.get_child(name)
        except AttributeError:
            raise FuseOSError(EPERM)
        except KeyError:
            raise FuseOSError(ENOENT)

        return node

