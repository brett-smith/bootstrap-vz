from . import tasks
from bootstrapvz.common import task_groups
from bootstrapvz.common.tasks import image
from bootstrapvz.common.tasks import ssh
from bootstrapvz.common.tasks import volume
import os


def validate_manifest(data, validator, error):
	schema_path = os.path.normpath(os.path.join(os.path.dirname(__file__), 'manifest-schema.yml'))
	validator(data, schema_path)


def resolve_tasks(taskset, manifest):
	taskset.update(task_groups.ssh_group)

	taskset.discard(image.MoveImage)
	taskset.discard(ssh.DisableSSHPasswordAuthentication)

	taskset.update([tasks.CheckOVAPath,
	                tasks.CreateOVADir,
	                tasks.PackageOVA,
	                tasks.RemoveOVADir,
	                volume.Delete,
	                ])


def resolve_rollback_tasks(taskset, manifest, completed, counter_task):
	counter_task(taskset, tasks.CreateOVADir, tasks.RemoveOVADir)
