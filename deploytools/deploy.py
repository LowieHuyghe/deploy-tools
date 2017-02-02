
from scriptcore.cuiscript import CuiScript
from deploytools.drivers.gae.gae import Gae


class Deploy(CuiScript):

    def __init__(self, base_path, arguments=None):
        """
        Construct the script
        :param base_path:   The base path
        :param arguments:   The arguments
        """

        title = 'Deploy'
        description = 'Helpers for deploying'

        super(Deploy, self).__init__(base_path, title, description, arguments=arguments)

        self._register_command('gae', 'Deploy on Google App Engine', Gae)
