
from deploytools.drivers.basedriver import BaseDriver
import os
import shutil
import re
from datetime import datetime


class Gae(BaseDriver):

    def __init__(self, base_path, arguments=None):
        """
        Construct the script
        :param base_path:   The base path
        :param arguments:   The arguments
        """

        title = 'GAE Deploy'
        description = 'Deploy on Google App Engine'

        super(Gae, self).__init__(base_path, title, description, arguments=arguments)

        self._register_command('production', 'Deploy application for production', lambda *args, **kwargs: self.deploy(self.PRODUCTION, *args, **kwargs))
        self._register_command('staging', 'Deploy application for staging', lambda *args, **kwargs: self.deploy(self.STAGING, *args, **kwargs))

    def deploy(self, environment, arguments=None):
        """
        Deploy
        :param environment: The environment to deploy in
        :param arguments:   The arguments
        :return:            void
        """

        try:
            self._deploy(environment, arguments=arguments)
            self.output('')
        finally:
            self._clean_up()

    def _deploy(self, environment, arguments=None):
        """
        Actually deploy
        :param environment: The environment to deploy in
        :param arguments:   The arguments
        :return:            void
        """

        # Prepare
        if not self._load_config():
            return False
        caching = self.config('caching', True)

        # Confirm deploy
        warnings = []
        if environment == self.PRODUCTION:
            warnings.append('Do not push any changes to app.yaml whilst deploying the application!')
        warnings.append('All database changes should be backwards compatible!')
        # Ask
        if not self._deploy_confirm(environment, warnings):
            return False
        self.output('')

        # Title
        self.output.title('Preparing deploy')
        self.output('')

        # Temp directory
        directory = self._get_temp_dir()
        self.output.info('Working dir: %s' % directory)

        # Git clone
        repo = self.config('repository')
        branch = self.config('branch')
        if not self._git_clone(environment, directory, repo, branch, caching=caching):
            return False

        # Copy persistent files
        if not self._copy_persistent_files(directory):
            return False

        # Load app.yaml
        app_yaml = self._get_app_yaml(directory)
        if not app_yaml:
            return False

        # Composer install
        if not self._composer_install(environment, directory, caching=caching):
            return False

        # Npm install
        if not self._npm_install(environment, directory, caching=caching):
            return False

        # Update app.yaml version
        if not self._update_app_yaml_version(environment, directory, app_yaml, branch):
            return False

        # Run custom commands
        if not self._run_custom_commands(environment, directory, branch):
            return False

        # Deploy application
        if not self._deploy_to_gae(directory):
            return False

        # Push new version
        if not self._git_push(environment, directory):
            return False

    def _load_config(self):
        """
        Load the config
        :return:    Dict
        """

        deploy_json_path = 'deploy.json'

        if not os.path.isfile(deploy_json_path):
            self.output.error('No \'%s\' found' % deploy_json_path)
            return False

        self.config.load_from_json('deploy.json')

        if self.config('repository') is None:
            self.output.error('\'repository\' is not set in deploy.json')
            return False
        if self.config('branch') is None:
            self.output.error('\'branch\' is not set in deploy.json')
            return False
        if self.config('persistent') is None:
            self.output.error('\'persistent\' is not set in deploy.json')
            return False
        if self.config('caching') is None:
            self.output.error('\'caching\' is not set in deploy.json')
            return False
        if self.config('commands') is None:
            self.output.error('\'commands\' is not set in deploy.json')
            return False

        return True

    def _copy_persistent_files(self, directory):
        """
        Copy persistent files
        :param directory:   The working directory
        :return:    Success
        """

        persistent_files = self.config('persistent', {})
        if not persistent_files:
            self.output.info('Skipped copying persistent files')
            return True

        def copy_persistent_files(persistent_files, directory):
            for persistent_file in persistent_files:
                shutil.copyfile(persistent_file, os.path.join(directory, persistent_files[persistent_file]))

        out, err, exitcode = self.execute.spinner(copy_persistent_files, 'Copying persistent files', (persistent_files, directory))
        if exitcode != 0:
            self.output.error('Failed copying persistent files')
            return False

        self.output.success('Successfully copied persistent files')
        return True

    def _get_app_yaml(self, directory):
        """
        Get app.yaml
        :param directory:   The working directory
        :return:            Dict
        """

        app_yaml = self._yaml_load(directory, 'app.yaml')
        if not app_yaml:
            return False

        if 'application' not in app_yaml or not app_yaml['application']:
            self.output.error('Google App Engine application was not set in app.yaml')
            return False

        if 'version' not in app_yaml or not app_yaml['version']:
            self.output.error('Google App Engine version was not set in app.yaml')
            return False

        return app_yaml

    def _update_app_yaml_version(self, environment, directory, app_yaml, branch):
        """
        Update the app yaml version
        param environment:  The environment
        param directory:    The working directory
        param app_yaml:     The current app yaml
        param branch:       The branch
        :return:            Success
        """

        # Version increase
        version = list()
        match = re.match('^(\d*)\D*(\d*)\D*(\d*)$', app_yaml['version'])
        version.append(int(match.group(1)) if match.group(1) else 0)
        version.append(int(match.group(2)) if match.group(2) else 0)
        version.append(int(match.group(3)) + 1 if match.group(3) else 0)
        if version[0] + version[1] + version[2] == 0:
            version[2] += 1
        version_string_underscore = '%i-%i-%i' % tuple(version)
        version_string_dot = '%i.%i.%i' % tuple(version)

        if environment == self.PRODUCTION:
            # Increase app yaml version
            command = 'sed -i.bak -e "s/^version[ \\t]*:[ \\t]*[0-9]*[^0-9\\n]*[0-9]*[^0-9\\n]*[0-9]*$/version: %s/" "%s/app.yaml"' % (version_string_underscore, directory)
            command += ' && rm -f %s/app.yaml.bak' % directory
            description = 'Increase version of app.yaml'
            out, err, exitcode = self.execute.spinner(command, description)
            if exitcode != 0:
                self.output.error('Failed to increase version of app.yaml')
                return False

            # Add file to git
            command = 'git --git-dir "%s/.git" --work-tree "%s" add app.yaml' % (directory, directory)
            description = 'Adding the increased app.yaml to git'
            out, err, exitcode = self.execute.spinner(command, description)
            if exitcode != 0:
                self.output.error('Failed adding the increased app.yaml to git')
                return False

            # Commit
            datetime_string = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            user = self._get_current_user()
            commit_title = 'Release of %s on %s UTC by %s' % (branch, datetime_string, user.name)
            commit_description = 'Released on Google App Engine application %s as version %s' % (app_yaml['application'], version_string_underscore)
            command = 'git --git-dir "%s/.git" --work-tree "%s" commit -m "%s" -m "%s"' % (directory, directory, commit_title, commit_description)
            description = 'Committing the increased app.yaml to git'
            out, err, exitcode = self.execute.spinner(command, description)
            if exitcode != 0:
                self.output.error('Failed committing the increased app.yaml to git')
                return False

            # Last hash
            command = 'git --git-dir "%s/.git" --work-tree "%s" rev-parse HEAD' % (directory, directory)
            description = 'Fetching the hash of the last commit'
            out, err, exitcode = self.execute.spinner(command, description)
            if exitcode != 0:
                self.output.error('Failed fetching the hash of the last commit')
                return False
            commit_hash = out[0]

            # Tag
            command = 'git --git-dir "%s/.git" --work-tree "%s" tag -a v%s -m "Version %s (%s)" %s' % (directory, directory, version_string_dot, version_string_dot, commit_title, commit_hash)
            description = 'Tagging the last commit as a new release'
            out, err, exitcode = self.execute.spinner(command, description)
            if exitcode != 0:
                self.output.error('Failed tagging the last commit as a new release')
                return False

        else:
            # Set application name
            app_yaml['application'] = '%s-%s' % (app_yaml['application'], environment)

            # Set version
            app_yaml['version'] = version_string_underscore

            # Set environment to staging
            if 'env_variables' not in app_yaml:
                app_yaml['env_variables'] = dict()
            app_yaml['env_variables']['APP_ENV'] = environment

            # All handlers should be secured with login
            if 'handlers' in app_yaml:
                for handler in app_yaml['handlers']:
                    handler['login'] = 'admin'

            # Dump the app.yaml
            if not self._yaml_dump(directory, 'app.yaml', app_yaml):
                return False

            # Also apply the environment to the .env files
            out, err, exitcode = self.execute('ls "%s/.env*"' % directory)
            if exitcode == 0:
                command = 'sed -i.bak -e "s/^APP_ENV[ \\t]*=[ \\t]*.*$/APP_ENV=%s/" "%s/.env*"' % (environment, directory)
                command += ' && rm -f "%s/.env*.bak"' % directory
                description = 'Updating .env-files'
                out, err, exitcode = self.execute.spinner(command, description)
                if exitcode != 0:
                    self.output.error('Failed updating .env-files')
                    return False

        self.output.success('Successfully increase version of application')
        return True

    def _run_custom_commands(self, environment, directory, branch):
        """
        Run the custom commands
        :param environment: The environment
        :param directory:   The working directory
        :param branch:      The branch
        :return:            Success
        """

        commands = self.config('commands', [])
        if not commands:
            self.output.info('Skipped custom commands')
            return True

        for command in commands:
            command = command.replace('{{environment}}', environment)
            command = command.replace('{{directory}}', directory)
            command = command.replace('{{branch}}', branch)

            description = 'Running \'%s\'' % command
            out, err, exitcode = self.execute.spinner(command, description)
            if exitcode != 0:
                self.output.error('Failed running \'%s\'\n%s' % (command, '.'.join(err)))
                return False
            else:
                self.output.success('Successfully ran \'%s\'' % command)

        return True

    def _deploy_to_gae(self, directory):
        """
        Deploy to Google App Engine
        :param directory:   The working directory
        :return:            Success
        """

        command = 'appcfg.py update "%s/."' % directory
        description = 'Deploying the app'
        out, err, exitcode = self.execute.spinner(command, description)
        if exitcode != 0:
            self.output.error('Failed deploying the app')
            return False

        self.output.success('Successfully deployed the app')
        return True

    def _git_push(self, environment, directory):
        """
        Push the changes in git
        :param environment: The environment
        :param directory:   The working directory
        :return:            Success
        """

        command = 'git --git-dir "%s/.git" --work-tree "%s" pull --rebase' % (directory, directory)
        description = 'Pulling git repository before pushing'
        out, err, exitcode = self.execute.spinner(command, description)
        if exitcode != 0:
            self.output.error('Failed pulling git repository before pushing')
            return False

        command = 'git --git-dir "%s/.git" --work-tree "%s" push --follow-tags' % (directory, directory)
        description = 'Pushing new version to repository'
        out, err, exitcode = self.execute.spinner(command, description)
        if exitcode != 0:
            self.output.error('Failed pushing new version to repository')
            return False

        self.output.success('Successfully pushed new version to repository')
        return True
