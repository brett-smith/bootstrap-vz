from bootstrapvz.common import task_groups
from bootstrapvz.common.tasks import loopback
from bootstrapvz.common.tasks import initd
from bootstrapvz.common.tasks import ssh
from bootstrapvz.common.tasks import apt
from bootstrapvz.common.tasks import grub

import bootstrapvz.common.tasks.image as commonimage

from .tasks import packages, boot, image


def validate_manifest(data, validator, error):
    from bootstrapvz.common.tools import rel_path
    validator(data, rel_path(__file__, 'manifest-schema.yml'))


def resolve_tasks(taskset, manifest):
    taskset.update(task_groups.get_standard_groups(manifest))
    taskset.update([apt.AddBackports,
                    packages.DefaultPackages,
                    loopback.AddRequiredCommands,
                    loopback.Create,
                    commonimage.MoveImage,
                    image.FixVHD,
                    initd.InstallInitScripts,
                    ssh.AddOpenSSHPackage,
                    ssh.ShredHostkeys,
                    ssh.AddSSHKeyGeneration,
                    boot.ConfigureGrub,
                    ])
    taskset.discard(grub.SetGrubConsolOutputDeviceToSerial)


def resolve_rollback_tasks(taskset, manifest, completed, counter_task):
    taskset.update(task_groups.get_standard_rollback_tasks(completed))
