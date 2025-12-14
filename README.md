# shellLLM
i'll add actual readme stuff here eventually

## usage
first clone the repo:
```bash
git clone https://github.com/carbonicality/shellLLM
```
then cd into it:
```bash
cd shellLLM
```
then, create a file called '.env' in the shellLLM folder with your API KEY:
```
touch .env && echo "API_KEY={your api key}" > .env
```
or, alternatively, just export your API KEY:
```bash
export API_KEY={your api key}
```

if you're trying to run this from something like ChromeOS VT2, try this:
export your API key:
```bash
export API_KEY={your api key}
```
and then run the file directly:
```bash
python3 <(curl https://raw.githubusercontent.com/carbonicality/shellLLM/main/main.py)
```
you might need to do it this way if you have a Read-only file system, like how ChromeOS does.