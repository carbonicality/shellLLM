# shellLLM
i'll add actual readme stuff here eventually

## online demo:
try the online demo at:
https://replit.com/@carbon06/shellLLM

make sure that, when you run it, you click "+ Tools and files", use the "Shell" option, and type:
`python3 main.py`

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
