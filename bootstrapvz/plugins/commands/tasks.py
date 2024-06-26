from bootstrapvz.base import Task
from bootstrapvz.common import phases
from bootstrapvz.plugins.file_copy.tasks import MkdirCommand
from bootstrapvz.plugins.file_copy.tasks import FileCopyCommand


class ImageExecuteCommand(Task):
    description = 'Executing commands in the image'
    phase = phases.user_modification
    predecessors = [MkdirCommand, FileCopyCommand]

    @classmethod
    def run(cls, info):
        from bootstrapvz.common.tools import log_check_call
        for raw_command in info.manifest.plugins['commands']['commands']:
            command = [part.format(root=info.root, **info.manifest_vars) for part in raw_command]
            shell = len(command) == 1
            log_check_call(command, shell=shell)
