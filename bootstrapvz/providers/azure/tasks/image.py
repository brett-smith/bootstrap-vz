import os
import re
import logging
from bootstrapvz.base import Task
from bootstrapvz.common import phases
from bootstrapvz.common.tasks import image
from bootstrapvz.common.tools import log_check_call

class FixVHD(Task):
    description = 'Preparing VHD for Azure'
    phase = phases.image_registration
    predecessors = [image.MoveImage]

    @classmethod
    def run(cls, info):

        log = logging.getLogger(__name__)

        # https://docs.microsoft.com/en-us/azure/virtual-machines/linux/create-upload-generic

        log.info('Converting to RAW format for alignment')

        image_name = info.manifest.name.format(**info.manifest_vars)
        destination_dir = info.manifest.bootstrapper['workspace'];
        destination = os.path.join(destination_dir, image_name + '.raw')
        src = os.path.join(destination_dir, image_name + '.' + info.volume.extension)

        # 1. Convert to RAW
        log_check_call(['qemu-img', 'convert', '-f', 'vpc',
                        '-O', 'raw', src,
                        destination
                       ])

        # 2. Extract image size in bytes and calculate the next MiB boundary
        log.info('Extracting image size')
        img_info = log_check_call(['qemu-img', 'info', '-f', 'raw', destination])
        regexp = re.compile('virtual size:.*')
        bytes = 0
        for line in img_info:
            match = regexp.match(line)
            if match is not None:
                bytes = int(line.split(' ')[3][1:])
        if bytes == 0:
            raise Exception('Could not determine image size')
        mb = 1024 * 1024
        sizemb = int(((bytes / mb) + 1) *mb)

        # 3. Resize the RAW image. Additional options are added for qemu 2.6+
        log.info('Resizing RAW format image for alignment (' + str(sizemb) + ' bytes)')
        log_check_call(['qemu-img', 'resize', '-f', 'raw', destination, str(sizemb)])

        format_opts = 'subformat=fixed'
        regexp = re.compile('.* (0\\.|1\\.|2\\.0|2\\.1|2\\.2|2\\.3|2\\.4|2\\.5).*')
        if not regexp.match(log_check_call(['qemu-img', '--version'])[0]):
            log.info('Using qemu-img 2.6+, adding force_size option')
            format_opts = 'subformat=fixed,force_size'

        # 4. Convert the RAW back to VHD
        log.info('Converting RAW format image back to VHD')
        log_check_call(['qemu-img', 'convert', '-f', 'raw', '-o', format_opts, '-O', 'vpc', destination, src])

        # 5. Clean up
        log.info('The volume image has been prepared for boot on Azure, removing RAW image.')
        os.remove(destination)
