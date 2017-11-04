# [DEPRECATED] Deploy Tools

Tools to easily deploy your application.


## Installation

1. Clone the project:

 ```bash
git clone git@github.com:LowieHuyghe/deploy-tools.git
```
2. Move into the new directory:

 ```bash
cd deploy-tools
```
3. Setup virtualenv and activate it
4. Install the requirements:

 ```bash
pip install -r requirements.txt
```


## Deploying

* [Google App Engine](#deploygoogleappengine)


<a href="#deploygoogleappengine"></a>
### Deploy Google App Engine

You can set the tool up in Google Cloud Shell, or locally. Whichever you prefer.

Features:
* Automatic composer install
* Automatic npm install
* Caching to speed up deploy
* Automatic increase of app.yaml-version
* Automatic release-commit and -tagging
* Custom commands


#### Setup

1. Create a separate directory for the deploy-files of your project.
2. Make a deploy.yaml file like so:

 ```yaml
deploy:
    name: Deploy tools
    repository: git@github.com:LowieHuyghe/deploy-tools.git
    branch: master
    caching: true
    persistent:
       relative/path/to/file/starting/from/deploy.yaml: relative/target/path
       /absolute/path/to/.env: relative/target/.env

before_all:
   - apt-get install php5-curl

before_deploy:
   - gulp --cwd {{directory}} build:prod
   - echo 'Other variables are {{environment}}, {{branch}}'

after_success:
    - echo 'The deploy was a great success'

after_failed:
    - echo 'The deploy has failed'

notifications:
    slack:
        webhook: https://hooks.slack.com/services/ABCDEFGHIJKLMNOPQRSTUVWXYZ
        channel: deploy-feed
        username: Deploy Bot
        icon: :robot_face:
```
  * **deploy**: General deploy config
    - **name**: Name of the project
    - **repository**: The repository to deploy
    - **branch**: The branch to deploy *(default: master)*
    - **caching**: Enable caching when cloning repo, doing npm install, doing composer install,... *(default: true)*
    - **persistent**: Persistent files (ideal for .env-files and similar) *(default: {})*
  * **before_all**: Custom commands to run first hand *(default: [])*. You can use variables that will be replaced at runtime:
    - `{{environment}}`: The current environment
    - `{{directory}}`: The working directory
    - `{{branch}}`: The deploy branch
  * **before_deploy**: Custom commands to run before deploying *(default: [])*. Same variables as *before_all* can be used.
  * **after_success**: Custom commands to run after successful deploy *(default: [])*. Same variables as *before_all* can be used.
  * **after_failed**: Custom commands to run after failed deploy *(default: [])*. Same variables as *before_all* can be used.
  * **notifications**
    - **slack**: Setup notification-callback for Slack while deploying
      - **webhook**: Webhook URL for Slack
      - **channel**: Channel to post notifications in
      - **username**: Username for Webhook
      - **icon**: Icon for Webhook
3. Start deploying:

 ```bash
python deploy.py gae
```

> Note: Make sure your virtualenv is active when running the script.


#### Deploy sequence timeline

This explains the timeline of the deploy sequence and which actions are done.

1. Load `deploy.yaml` and check required properties.
2. Confirm that the user wants to deploy.
3. Make a temporary working dir.
4. Run the before all commands described in `deploy.yaml`.
5. Clone the git repo and checkout the given branch. When caching is enabled,
the repo will be cached and reused on next deploy (when reusing, the repo is
fetched and reset to the remote). 
6. Copy the persistent files described in deploy.yaml to the working directory.
7. When composer.json is available, run `composer install (--no-dev)`.
8. When package.json is available, run `npm install (--production)`.
9. Update `app.yaml`:
  * Production:
    - Increase patch-version
    - Commit as new release
    - Tag as new release
  * Else:
    - Change `application` to `ORIGINALAPPLICATION_{{environment}}`
    - Increase patch-version
    - Add `APP_ENV: {{environment}}` to `env_variables`
    - Require `login: admin` for each handler ([more info](https://cloud.google.com/appengine/docs/python/config/appref#handlers_login))
    - Also apply `APP_ENV: {{environment}}` to any `.env*`-files
10. Run the before deploy commands described in `deploy.yaml`.
11. Deploy the application to Google App Engine.
12. If deploy failed, run the after failed commands.
13. If production, push the new commit and tag to the repository.
14. If deploy succeeded, run the after success commands.
15. Done.
