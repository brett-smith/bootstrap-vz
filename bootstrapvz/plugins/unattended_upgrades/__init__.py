

def validate_manifest(data, validator, error):
    from bootstrapvz.common.tools import rel_path
    validator(data, rel_path(__file__, 'manifest-schema.yml'))


def resolve_tasks(taskset, manifest):
    from . import tasks
    taskset.add(tasks.AddUnattendedUpgradesPackage)
    taskset.add(tasks.EnablePeriodicUpgrades)
