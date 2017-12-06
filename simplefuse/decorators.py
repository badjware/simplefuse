import logging

from simplefuse.filesystem import Filesystem, Node
from errno import EPERM, EROFS
from fuse import FuseOSError

logger = logging.getLogger(__name__)

def readonly(node_class):
    noop = None
    if issubclass(node_class, Filesystem):
        def noop(self, *args, **kwargs):
            raise FuseOSError(EROFS)
    elif issubclass(node_class, Node):
        def noop(self, *args, **kwargs):
            raise FuseOSError(EPERM)
    else:
        logger.warning("@readonly decorator on an incompatiple class: %s", node_class)
        return node_class

    member_to_noop = ('chmod', 'chown', 'create', 'mkdir', 'removexattr', 'rename', 'rmdir', 'setxattr', 'symlink', 'truncate', 'unlink', 'utimes', 'write')

    for member in dir(node_class):
        if callable(getattr(node_class, member)) and member in member_to_noop:
            setattr(node_class, member, noop)

    return node_class

def writeonly(node_class):
    noop = None
    if issubclass(node_class, Filesystem):
        def noop(self, *args, **kwargs):
            raise FuseOSError(EROFS)
    elif issubclass(node_class, Node):
        def noop(self, *args, **kwargs):
            raise FuseOSError(EPERM)
    else:
        logger.warning("@writeonly decorator on an incompatiple class: %s", node_class)
        return node_class

    member_to_noop = ('chmod', 'chown', 'open', 'read', 'readdir')

    for member in dir(node_class):
        if callable(getattr(node_class, member)) and member in member_to_noop:
            setattr(node_class, member, noop)

    return node_class