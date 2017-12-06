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
        self.set_ctime()

    def getattr(self, fh=None):
        return self.attr

    def getxattr(self, name, position):
        try:
            return self.attr[name]
        except KeyError:
            raise FuseOSError(ENOATTR)

    def removexattr(self, name):
        try:
            del self.attr[name]
        except KeyError:
            raise FuseOSError(ENOATTR)

    def setxattr(self, name, value, options, position=0):
        self.attr[name] = value

    def utimes(self, times=None):
        now = time()
        atime, mtime = times if times else (now, now)

        self.attr['st_atime'] = atime
        self.attr['st_mtime'] = mtime

    def set_ctime(self, times=None):
        if times is None:
            times = time()
        self.attr['st_ctime'] = times
    
    def set_mtime(self, times=None):
        if times is None:
            times = time()
        self.attr['st_ctime'] = times
        self.attr['st_mtime'] = times
        print(times)

    def set_atime(self, times=None):
        if times is None:
            times = time()
        self.attr['st_atime'] = times

    def __str__(self):
        return self.name


class Directory(Node):
    def __init__(self, name):
        super().__init__(name)
        self.attr['st_mode'] = (0o755 | S_IFDIR)
        self.fd = 0
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
        self.set_ctime()

    def create(self, name, mode):
        node = File(name)
        node.attr['st_mode'] = mode | S_IFREG
        self.add_child(name, node)
        self.fd += 1
        self.set_ctime()
        return self.fd

    def mkdir(self, name, mode):
        node = Directory(name)
        self.attr['st_mode'] = mode | S_IFDIR
        self.add_child(name, node)

        self.attr['st_nlink'] += 1
        self.set_mtime()

    def readdir(self, fh):
        yield '.'
        yield '..'
        for directory in self.children.keys():
            yield directory
        self.set_atime()

    def rename(self, old_name, new_name, new_parent_node):
        node = self.remove_child(old_name)
        new_parent_node.add_child(new_name, node)
        self.set_mtime()
        new_parent_node.set_mtime()
        node.set_ctime()

    def rmdir(self, name):
        self.remove_child(name)

        self.attr['st_nlink'] -= 1
        self.set_mtime()

    def symlink(self, name, target):
        node = Symlink(name, target)
        self.add_child(name, node)
        self.set_mtime()

    def unlink(self, name):
        self.remove_child(name)
        self.set_mtime()


class File(Node):
    def __init__(self, name):
        super().__init__(name)
        self.attr['st_mode'] = (0o755 | S_IFREG)
        self.fd = 0
        self.content = b''

    def chmod(self, mode):
        self.attr['st_mode'] = mode | S_IFREG
        self.set_ctime()

    def open(self, flags):
        self.fd += 1
        return self.fd

    def read(self, length, offset, fh):
        self.set_atime()
        return self.content[offset:offset+length]

    def write(self, buffer, offset):
        self.content = self.content[:offset] + buffer
        self.attr['st_size'] = len(self.content)
        self.set_mtime()

    def truncate(self, length):
        self.content = self.content[:length]
        self.set_mtime()


class Symlink(Node):
    def __init__(self, name, target):
        super().__init__(name)
        self.attr['st_mode'] = (0o755 | S_IFLNK)
        self.target = target

    def readlink(self):
        self.set_atime()
        return self.target


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
        return node.create(name, mode)

    def getattr(self, path, fh=None):
        node = self._get_node(path)
        return node.getattr(fh)

    def getxattr(self, path, name, position=0):
        node = self._get_node(path)
        return node.getxattr(name, position)

    def listxattr(self, path):
        node = self._get_node(path)
        return node.attr.keys()

    def mkdir(self, path, mode):
        parent_path, name = os.path.split(path)
        node = self._get_node(parent_path)
        node.mkdir(name, mode)

    def open(self, path, flags):
        node = self._get_node(path)
        return node.open(flags)

    def read(self, path, size, offset, fh):
        node = self._get_node(path)
        return node.read(size, offset, fh)

    def readdir(self, path, fh):
        node = self._get_node(path)
        return node.readdir(fh)

    def readlink(self, path):
        node = self._get_node(path)
        return node.readlink()

    def removexattr(self, path, name):
        node = self._get_node(path)
        node.removexattr(name)

    def rename(self, old, new):
        # TODO
        old_parent_path, old_name = os.path.split(old)
        new_parent_path, new_name = os.path.split(new)
        old_parent_node = self._get_node(old_parent_path)
        new_parent_node = self._get_node(new_parent_path)

        old_parent_node.rename(old_name, new_name, new_parent_node)

    def rmdir(self, path):
        parent_path, name = os.path.split(path)
        node = self._get_node(parent_path)
        node.rmdir(name)

    def setxattr(self, path, name, value, options, position=0):
        node = self._get_node(path)
        node.setxattr(name, value, options, position)

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
        node.utime(times)

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

