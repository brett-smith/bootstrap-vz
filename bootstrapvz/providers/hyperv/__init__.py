from bootstrapvz.common import task_groups
from bootstrapvz.providers.hyperv.tasks import packages
from bootstrapvz.common.tasks import image
from bootstrapvz.common.tasks import loopback
from bootstrapvz.common.tasks import initd
from bootstrapvz.common.tasks import ssh
from bootstrapvz.common.tasks import apt


def validate_manifest(data, validator, error):
	import os.path
	schema_path = os.path.normpath(os.path.join(os.path.dirname(__file__), 'manifest-schema.yml'))
	validator(data, schema_path)


def resolve_tasks(taskset, manifest):
	taskset.update(task_groups.get_standard_groups(manifest))
	taskset.update([apt.AddBackports,
	                packages.DefaultPackages,
	                loopback.AddRequiredCommands,
	                loopback.Create,
	                image.MoveImage,
	                initd.InstallInitScripts,
	                ssh.AddOpenSSHPackage,
	                ssh.ShredHostkeys,
	                ssh.AddSSHKeyGeneration,
	                ])


def resolve_rollback_tasks(taskset, manifest, completed, counter_task):
	taskset.update(task_groups.get_standard_rollback_tasks(completed))
