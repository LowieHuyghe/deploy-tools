
from scriptcore.cuiscript import CuiScript
from scriptcore.encoding.encoding import Encoding
from deploytools.models.user import User
import tempfile
import os
import json
import yaml
import shutil


class BaseDriver(CuiScript):

    PRODUCTION = 'production'
    STAGING = 'staging'
    DEVELOPMENT = 'development'

    def __init__(self, *args, **kwargs):
        """
        Construct the script
        """

        super(BaseDriver, self).__init__(*args, **kwargs)

        self._temp_dirs = []

    def _get_temp_dir(self):
        """
        Get temporary directory
        :return:    Directory path
        """

        temp_dir = tempfile.mkdtemp()
        self._temp_dirs.append(temp_dir)

        return temp_dir

    def _clean_up(self):
        """
        Clean up
        :return:
        """

        for temp_dir in self._temp_dirs:
            shutil.rmtree(temp_dir)
        self._temp_dirs = []

    def _deploy_confirm(self, environment, warnings=None):

        user = self._get_current_user()
        self.output.title('Beginning %s deploy sequence by %s' % (environment, user.name))
        self.output('')

        if warnings is not None:
            for warning in warnings:
                self.output.warning(warning)
            self.output('')

        if not self.input.yes_no('Do you really wish to deploy this application?'):
            self.output.error('Deploy aborted')
            return False

        self.output.success('Let\'s do this!')
        return True

    def _git_clone(self, environment, directory, repo, branch, caching=True):
        """
        Clone repository
        :param environment: The environment
        :param directory:   THe directory
        :param repo:        The link to the repo
        :param branch:      The branch to checkout
        :param caching:     Caching
        :return:            Success
        """

        # Cache exists
        cache_exists = os.path.isfile('./git.cache.tar')

        # Extract cache
        if caching and cache_exists:
            command = 'tar xf ./git.cache.tar -C "%s"' % directory
            description = 'Extracting cached git repository'
            out, err, exitcode = self.execute.spinner(command, description)
            if exitcode != 0:
                self.output.error('Failed extracting cached git repository\n%s' % '\n'.join(err))
                return False

            # Check remote url of cache
            command = 'if [ ! "$( git --git-dir "%s/.git" --work-tree "%s" config --get remote.origin.url )" = "%s" ]; then exit 1; else exit 0; fi' % (directory, directory, repo)
            description = 'Checking cached git repository'
            out, err, exitcode = self.execute.spinner(command, description)
            if exitcode == 1:
                self.output.error('Failed as repository of "./git.cache.tar" != repository in deploy.json')
                return False

        # Git clone
        if not caching or not cache_exists:
            command = 'git clone "%s" "%s"' % (repo, directory)
            description = 'Cloning repository \'%s\'' % repo
            out, err, exitcode = self.execute.spinner(command, description)
            if exitcode != 0:
                self.output.error('Failed cloning repository \'%s\'\n%s' % (repo, '\n'.join(err)))
                return False

        # Checkout branch
        command = 'git --git-dir "%s/.git" --work-tree "%s" checkout %s' % (directory, directory, branch)
        description = 'Checking out branch \'%s\'' % branch
        out, err, exitcode = self.execute.spinner(command, description)
        if exitcode != 0:
            self.output.error('Failed checking out branch \'%s\'\n%s' % (branch, '\n'.join(err)))
            return False

        # Fetch origin
        if caching and cache_exists:
            command = 'git --git-dir "%s/.git" --work-tree "%s" fetch origin' % (directory, directory)
            description = 'Fetching from origin'
            out, err, exitcode = self.execute.spinner(command, description)
            if exitcode != 0:
                self.output.error('Failed fetching from origin\n%s' % '\n'.join(err))
                return False

        # Reset to origin
        if caching and cache_exists:
            command = 'git --git-dir "%s/.git" --work-tree "%s" reset --hard origin' % (directory, directory)
            description = 'Resetting to origin'
            out, err, exitcode = self.execute.spinner(command, description)
            if exitcode != 0:
                self.output.error('Failed resetting to origin\n%s' % '\n'.join(err))
                return False

        # Caching git repo
        if caching:
            command = 'tar cf ./git.cache.tar -C "%s" .' % directory
            description = 'Caching git repository'
            out, err, exitcode = self.execute.spinner(command, description)
            if exitcode != 0:
                self.output.error('Failed caching git repository\n%s' % '\n'.join(err))
                return False

        self.output.success('Successfully cloned repository \'%s#%s\'' % (repo, branch))
        return True

    def _composer_install(self, environment, directory, caching=True):
        """
        Composer install
        :param environment: The environment
        :param directory:   The directory
        :param caching:     Caching
        :return:            Success
        """

        composer_json = os.path.join(directory, 'composer.json')
        if not os.path.isfile(composer_json):
            self.output.info('Skipped composer install')
            return True

        # Cache exists
        cache_exists = os.path.isfile('./composer.cache.tar')

        # Extract cache
        if caching and cache_exists:
            command = 'tar xf ./composer.cache.tar -C "%s"' % directory
            description = 'Extracting cached composer install'
            out, err, exitcode = self.execute.spinner(command, description)
            if exitcode != 0:
                self.output.error('Failed extracting cached composer install\n%s' % '\n'.join(err))
                return False

        # Composer install
        command = 'composer --working-dir="%s" install' % directory
        if environment == self.PRODUCTION or environment == self.STAGING:
            command += ' --no-dev'
        description = 'Running composer install'
        out, err, exitcode = self.execute.spinner(command, description)
        if exitcode != 0:
            self.output.error('Failed running composer install\n%s' % '\n'.join(err))
            return False

        # Caching composer install
        if caching:
            command = 'tar cf ./composer.cache.tar -C "%s" vendor' % directory
            description = 'Caching composer install'
            out, err, exitcode = self.execute.spinner(command, description)
            if exitcode != 0:
                self.output.error('Failed caching composer install\n%s' % '\n'.join(err))
                return False

        self.output.success('Successfully ran composer install')
        return True

    def _npm_install(self, environment, directory, caching=True):
        """
        Npm install
        :param environment: The environment
        :param directory:   THe directory
        :param caching:     Caching
        :return:            Success
        """

        package_json = os.path.join(directory, 'package.json')
        if not os.path.isfile(package_json):
            self.output.info('Skipped npm install')
            return True

        # Cache exists
        cache_exists = os.path.isfile('./npm.cache.tar')

        # Extract cache
        if caching and cache_exists:
            command = 'tar xf ./npm.cache.tar -C "%s"' % directory
            description = 'Extracting cached npm install'
            out, err, exitcode = self.execute.spinner(command, description)
            if exitcode != 0:
                self.output.error('Failed extracting cached npm install\n%s' % '\n'.join(err))
                return False

        # Prune cached
        if caching and cache_exists:
            command = 'npm prune --prefix "%s"' % directory
            description = 'Pruning cached npm install'
            out, err, exitcode = self.execute.spinner(command, description)
            if exitcode != 0:
                self.output.error('Failed pruning cached npm install\n%s' % '\n'.join(err))
                return False

        # Npm install
        command = 'npm install --prefix "%s"' % directory
        if environment == self.PRODUCTION or environment == self.STAGING:
            command += ' --production'
        description = 'Running npm install'
        out, err, exitcode = self.execute.spinner(command, description)
        if exitcode != 0:
            self.output.error('Failed running npm install\n%s' % '\n'.join(err))
            return False

        # Caching npm install
        if caching:
            command = 'tar cf ./npm.cache.tar -C "%s" node_modules' % directory
            description = 'Caching npm install'
            out, err, exitcode = self.execute.spinner(command, description)
            if exitcode != 0:
                self.output.error('Failed caching npm install\n%s' % '\n'.join(err))
                return False

        self.output.success('Successfully ran npm install')
        return True

    def _submodules_update(self, environment, directory):
        """
        Update submodules
        :param environment: The environment
        :param directory:   THe directory
        :return:            Success
        """

        # Submodule update
        # Note: submodule-command requires to be in the working directory instead of --work-tree
        command = 'cd "%s" && git --git-dir "%s/.git" submodule update --init --recursive' % (directory, directory)
        description = 'Updating submodules'
        out, err, exitcode = self.execute.spinner(command, description)
        if exitcode != 0:
            self.output.error('Failed updating submodules\n%s' % '\n'.join(err))
            return False

        self.output.success('Successfully updated submodules')
        return True

    def _get_current_user(self):
        """
        Get the current user
        :return:    User
        """

        out, err, exitcode = self.execute('whoami')

        if exitcode == 0:
            return User(out[0])
        return None

    def _yaml_load(self, directory, filename):
        """
        Load yaml file
        :param directory:   The working directory
        :param filename:    The file to load
        :return:            Dict
        """

        yaml_path = os.path.join(directory, filename)

        if not os.path.isfile(yaml_path):
            self.output.error('No \'%s\' found' % filename)
            return False

        yaml_file = open(yaml_path)
        try:
            yaml_content = yaml.safe_load(yaml_file)
        except OSError:
            self.output.error('Could not load \'%s\'' % filename)
            return False
        finally:
            yaml_file.close()

        return yaml_content

    def _yaml_dump(self, directory, filename, content):
        """
        Dump the yaml into a yaml file
        :param directory:   The working directory
        :param filename:    The file to dump to
        :param content:     The content
        :return:            Success
        """

        yaml_path = os.path.join(directory, filename)

        yaml_file = open(yaml_path, 'w')
        try:
            yaml.dump(content, yaml_file)
        except OSError:
            self.output.error('Could not dump yaml into \'%s\'' % filename)
            return False
        finally:
            yaml_file.close()

        return True

    def _json_load(self, directory, filename):
        """
        Load json file
        :param directory:   The working directory
        :param filename:    The file to load
        :return:            Dict
        """

        json_path = os.path.join(directory, filename)

        if not os.path.isfile(json_path):
            self.output.error('No \'%s\' found' % filename)
            return False

        json_file = open(json_path)
        try:
            json_content = Encoding.normalize(json.load(json_file))
        except OSError:
            self.output.error('Could not load \'%s\'' % filename)
            return False
        finally:
            json_file.close()

        return json_content
