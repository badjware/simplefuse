import logging

from simplefuse.filesystem import Filesystem


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s:%(levelname)s:%(message)s"
)

fs = Filesystem()
fs.mount('/home/marchambault/mnt')
