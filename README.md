# shellLLM
## what is shellLLM?
shellLLM is an application built in Python which essentially acts as a 'frontend' to talk to an AI, using an API key. i built this application with Hack Club API keys in mind.

this project was built for the Hack Club dummies YSWS, and I made this so that I can practice and improve my python skills.

you'll need to provide an API key yourself to use this.
you can get help on how to use it by typing '::help' or '::nav' and then pressing 'h'.

thanks for reading!

## online demo:
try the online demo at:
https://replit.com/@carbon06/shellLLM

to use the online demo:
1. click the run button so that it installs dependencies (ignore the error in Console)
2. press '+ Tools and files', and search Shell, and click Shell
3. type 'python3 main.py', and there you go! you're running shellLLM!

## usage
first clone the repo:
```bash
git clone https://github.com/carbonicality/shellLLM
```
then cd into it:
```bash
cd shellLLM
```
and run the file:
```bash
python3 main.py
```

### another way to use it
if you're trying to run this from something like ChromeOS VT2, try this:
```bash
python3 <(curl https://raw.githubusercontent.com/carbonicality/shellLLM/main/main.py)
```
you might need to do it this way if you have a Read-only file system, like how ChromeOS does.

### if you want to use a .env or environment variable:
if you want to use a .env file, cd into the shellLLM directory and:
```bash
touch .env && echo "API_KEY={your api key}" > .env
```
alternatively, if you want to use an environment variable:
```bash
export API_KEY={your api key}
```
this will stop it from prompting you to enter your API KEY on launch.
