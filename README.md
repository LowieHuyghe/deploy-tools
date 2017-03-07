# Deploy Tools

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
2. Make a deploy.json file like so:

 ```json
{
    "repository": "git@github.com:LowieHuyghe/deploy-tools.git",
    "branch": "master",
    "caching": true,
    "persistent": {
        "relative/path/to/file/starting/from/deploy.json": "relative/target/path",
        "/absolute/path/to/.env": "relative/target/.env"
    },
    "before_commands": [
        "apt-get install php5-curl"
    ],
    "after_commands": [
        "gulp --cwd {{directory}} build:prod",
        "echo 'Other variables: {{environment}}, {{branch}}'"
    ]
}
```
  * **repository**: The repository to deploy
  * **branch**: The branch to deploy
  * **caching**: Enable caching when cloning repo, doing npm install, doing composer install,...
  * **persistent**: Persistent files (ideal for .env-files and similar)
  * **before_commands**: Custom commands to run first hand. You can use variables that will be replaced at runtime:
    - `{{environment}}`: The current environment
    - `{{directory}}`: The working directory
    - `{{branch}}`: The deploy branch
  * **after_commands**: Custom commands to run before deploying. Same variables as *before_commands* can be used.
3. Start deploying:

 ```bash
python deploy.py gae
```

> Note: Make sure your virtualenv is active when running the script.


#### Deploy sequence timeline

This explains the timeline of the deploy sequence and which actions are done.

1. Load `deploy.json` and check required properties.
2. Confirm that the user wants to deploy.
3. Make a temporary working dir.
4. Run the before commands described in `deploy.json`.
5. Clone the git repo and checkout the given branch. When caching is enabled,
the repo will be cached and reused on next deploy (when reusing, the repo is
fetched and reset to the remote). 
6. Copy the persistent files described in deploy.json to the working directory.
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
10. Run the after commands described in `deploy.json`.
11. Deploy the application to Google App Engine.
12. If production, push the new commit and tag to the repository.
13. Done.
