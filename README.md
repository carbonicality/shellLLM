# shellLLM
i'll add actual readme stuff here eventually

## usage
`git clone https://github.com/carbonicality/shellLLM`
`cd shellLLM`
then, create a file called '.env' in the shellLLM folder with your API KEY:
`touch .env && echo "API_KEY={your api key}" > .env`
or, alternatively, just export your API KEY:
`export API_KEY={your api key}`

if you're trying to run this from something like ChromiumOS VT2, try this:
`export API_KEY={your api key}`
`python3 <(curl https://raw.githubusercontent.com/carbonicality/shellLLM/main/main.py)`