import logging

from simplefuse.filesystem import Filesystem
from simplefuse.helpers import DictDirectory


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s:%(levelname)s:%(message)s"
)

test_dict = {
    "hello": "Hello World!",
    "subfolder": {
        "foo": "bar"
    }
}

#fs = Filesystem(DictDirectory(test_dict), '/home/marchambault/mnt')
fs = Filesystem()
fs.mount('/home/marchambault/mnt')
