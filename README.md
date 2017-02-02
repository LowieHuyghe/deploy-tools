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
    // The repository to deploy
    "repository": "git@github.com:LowieHuyghe/deploy-tools.git",
    // The branch to deploy
    "branch": "master",
    // Enable caching when cloning repo, doing npm install, doing composer install,...
    "caching": true,
    // Persistent files (ideal for .env-files and similar)
    "persistent": {
        "relative/path/to/file/starting/from/deploy.json": "relative/target/path",
        "/absolute/path/to/.env": "relative/target/.env"
    },
    // Custom commands to run before deploying
    "commands": [
        "gulp --cwd {{directory}} build:prod",
        "echo 'Other variables: {{environment}}, {{branch}}'"
    ]
}
```

3. Start deploying:

 ```bash
python deploy.py gae
```

> Note: Make sure your virtualenv is active when running the script.
