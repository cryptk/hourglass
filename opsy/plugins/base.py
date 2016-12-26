import abc
import six


@six.add_metaclass(abc.ABCMeta)
class BaseOpsyPlugin(object):
    """Base class for plugins."""

    def __init__(self, app):
        pass

    @abc.abstractproperty
    def name(self):
        """This should just return the name of the plugin.

        :rtype: String
        """

    @abc.abstractproperty
    def config_options(self):
        """This should return a list of all config options for the plugin.

        :rtype: list
        """

    @abc.abstractproperty
    def needs(self):
        """This should provide a dict of all the needs for this plugin.

        :rtype: Dict
        """

    def _parse_config(self, app):
        """Perform any config parsing necessary for the plugin.

        :param app: Flask app object
        :type app: Flask
        :return: Flask app object
        :rtype: Flask
        """

    @abc.abstractmethod
    def register_blueprints(self, app):
        """Register any blueprints that the plugin provides.

        :param app: Flask app object
        :type app: Flask
        :return: Flask app object
        :rtype: Flask
        """

    @abc.abstractmethod
    def register_link_structure(self, app):
        """Register a link structure for the plugin.

        :param app: Flask app object
        :type app: Flask
        :return: Dictionary
        :rtype: Dict
        """

    @abc.abstractmethod
    def register_scheduler_jobs(self, app, run_once=False):
        """Register any scheduler jobs for the plugin.

        :param app: Flask app object
        :type app: Flask
        :param run_once: Control if the jobs are scheduled once
        :type run_once: bool
        """

    @abc.abstractmethod
    def register_cli_commands(self, cli):
        """Register any cli commands for the plugin."""

    @abc.abstractmethod
    def register_shell_context(self, shell_ctx):
        """Register any objects for the plugin on the shell context.

        :param shell_ctx: Shell variables dict
        :type shell_ctx: Dict
        """
