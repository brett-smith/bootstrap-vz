from bootstrapvz.base import Task
from bootstrapvz.common import phases
from bootstrapvz.common.tasks import grub
from bootstrapvz.common.tasks import kernel
import os

class ConfigureGrub(Task):
    description = 'Change grub configuration to allow for ttyS0 output'
    phase = phases.system_modification
    successors = [grub.WriteGrubConfig]

    @classmethod
    def run(cls, info):
        info.grub_config['GRUB_CMDLINE_LINUX'].extend([
            'console=tty0',
            'console=ttyS0,115200n8',
            'earlyprintk=ttyS0,115200',
        ])
