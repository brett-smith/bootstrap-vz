from qemuvolume import QEMUVolume
from ..tools import log_check_call
import math

class VirtualHardDisk(QEMUVolume):

    extension = 'vhd'
    qemu_format = 'vpc'
    ovf_uri = 'http://go.microsoft.com/fwlink/?LinkId=137171'

    # Azure requires the image size to be a multiple of 1 MiB.
    # VHDs are dynamic by default, so we add the option
    # to make the image size fixed (subformat=fixed)
    def _before_create(self, e):
        self.image_path = e.image_path
        vol_size = str(self.size.bytes.get_qty_in('MiB')) + 'M'
        log_check_call(['qemu-img', 'create', '-o', 'subformat=fixed', '-f', self.qemu_format, self.image_path + '.tmp', vol_size])
        # https://serverfault.com/questions/770378/problems-preparing-a-disk-image-for-upload-to-azure
        # Note, this doesn't seem to work if you try and create with the force_size option, it must be in convert
        log_check_call(['qemu-img', 'convert', '-f', 'raw', '-O', self.qemu_format, '-o', 'subformat=fixed,force_size', self.image_path + '.tmp', self.image_path])
        log_check_call(['rm', self.image_path + '.tmp'])

    def get_uuid(self):
        if not hasattr(self, 'uuid'):
            import uuid
            self.uuid = uuid.uuid4()
        return self.uuid
