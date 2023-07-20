from argparse import ArgumentParser, FileType, _StoreTrueAction
from importlib import import_module
from typing import Dict

from django.conf import settings
from django.core.management import BaseCommand, get_commands, load_command_class


class CommandInfo:
    def __init__(self, app: str, name: str, instance: BaseCommand):
        self.app = app
        self.name = name
        self.instance = instance
        self._arg_parser = None

    @property
    def arg_parser(self) -> ArgumentParser:
        if self._arg_parser is None:
            self._arg_parser = self.instance.create_parser('', self.name)
        return self._arg_parser

    @property
    def uses_doit(self):
        return any(a.dest == 'doit' for a in self.arg_parser._actions)

    @property
    def args(self):
        # create a test command to get the arguments which are shared by all commands
        # so that we can filter them out
        base_command = BaseCommand()
        base_parser = base_command.create_parser('', self.name)
        default_args = [a.dest for a in base_parser._actions]
        return [
            action
            for action in self.arg_parser._actions
            if action.dest != 'doit' and action.dest not in default_args
        ]

    @classmethod
    def serialize_arg(cls, arg):
        return {
            'name': arg.dest,
            'help': arg.help,
            'required': arg.required,
            'default': arg.default,
            'type': cls.arg_type_str(arg),
        }

    @classmethod
    def arg_type_str(cls, arg) -> str:
        if isinstance(arg, _StoreTrueAction):
            typ = 'bool'
        elif arg.type is open or isinstance(arg.type, FileType):
            typ = 'file'
        elif arg.type:
            typ = arg.type.__name__
        else:
            typ = None
        return typ


class CommandManager:
    def __init__(self):
        all_commands = get_commands()
        # validate commands against the list of available commands
        self._commands: Dict[str, str] = {
            name: app for app, name in self._list_commands() if all_commands.get(name) == app
        }

    @classmethod
    def _list_commands(cls) -> [(str, str)]:
        """
        Returns a list of tuples (app_name, command_name)
        """
        return settings.EXPOSED_MANAGEMENT_COMMANDS

    @classmethod
    def get_invalid_exposed_commands(cls) -> [(str, str)]:
        """
        Returns a list of tuples (app_name, command_name) which are listed as exposed but are not
        available.
        """
        invalid = []
        all_commands = get_commands()
        exposed_commands = cls._list_commands()
        for app, command in exposed_commands:
            if all_commands.get(command) != app:
                invalid.append((app, command))
        return invalid

    @classmethod
    def _resolve_command(cls, app, command):
        module = import_module(f'{app}.management.commands.{command}')
        return getattr(module, 'Command')

    @property
    def commands(self) -> [CommandInfo]:
        """
        Returns a list of CommandInfo objects
        """
        return [self.get_command_by_name(name) for name in self._commands.keys()]

    def get_command_by_name(self, command_name: str) -> CommandInfo:
        """
        Returns a CommandInfo object for the given command name
        """
        try:
            app = self._commands[command_name]
        except KeyError:
            return None
        instance = load_command_class(app, command_name)
        return CommandInfo(app, command_name, instance)
