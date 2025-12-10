import requests
import os
import json
import sys
from datetime import datetime

def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key,value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# i asked AI for some colour codes, it gave me these so i used AI here
class Colours:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

def print_c(text, colour='', end='\n'):
    # print coloured text
    print(f"{colour}{text}{Colours.RESET}", end=end)
    sys.stdout.flush()

def print_h(text):
    # print header
    width = 80
    print_c('=' * width, Colours.CYAN)
    print_c(text.center(width), Colours.CYAN + Colours.BOLD)
    print_c('=' * width, Colours.CYAN)

def print_sep():
    # print separator
    print_c('-' * 80, Colours.DIM)

class mainChat:
    def __init__(self,api_key=None, base_url="https://ai.hackclub.com/proxy/v1", model="openai/gpt-5.1"):
        self.api_key = api_key or os.environ.get("API_KEY")
        if not self.api_key:
            raise ValueError("api key not found, is the API key in .env?")
        self.base_url = base_url
        self.model = model
        self.convo_history = []
    
    def send_msg(self, user_msg, stream=True):
        self.convo_history.append({
            "role": "user",
            "content": user_msg
        })
        
        if stream:
            return self._stream_res()
        else:
            return self._get_res()

    def _stream_res(self):
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": self.convo_history,
            "stream": True
        }
        full_res = ""

        try:
            res = requests.post(url, headers=headers, json=data, stream=True, timeout=30)
            res.raise_for_status()
            for line in res.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        line = line[6:]
                        if line.strip() == '[DONE]':
                            break
                        try:
                            chunk = json.loads(line)
                            if 'choices' in chunk and len(chunk['choices']) > 0:
                                delta = chunk['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    full_res += content
                                    yield content
                        except json.JSONDecodeError:
                            continue
            self.convo_history.append({
                "role": "assistant",
                "content": full_res
            })
        except requests.exceptions.RequestException as e:
            return f"error: {str(e)}"
    
    def clear_hist(self):
        self.convo_history = []
    
    def get_msg_count(self):
        return len(self.convo_history)

def main():
    load_env()
    api_key = os.environ.get("API_KEY")
    if not api_key:
        print_c("error: api key not set", Colours.RED + Colours.BOLD)
        print_c("create a .env file with API_KEY=your-key-here, that's named '.env',", Colours.YELLOW)
        print_c("or set an environment variable: export API_KEY=your-key-here", Colours.YELLOW)
        return
    model = "openai/gpt-5.1"
    try:
        chat = mainChat(api_key, model=model)
    except ValueError as e:
        print_c(f"error: {e}", Colours.RED)
        return
    print_h("shellLLM")
    print_c(f"model: {model}", Colours.CYAN)
    print_c("commands: 'quit' or 'exit' to quit, 'clear' to clear history", Colours.DIM)
    print_sep()
    print()

    while True:
        try:
            print_c("You: ", Colours.GREEN + Colours.BOLD, end='')
            user_input = input().strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        if not user_input:
            continue
        if user_input.lower() in ['quit','exit']:
            break
        if user_input.lower() == 'clear':
            chat.clear_hist()
            print_c("history cleared.", Colours.YELLOW)
            print()
            continue
        print()
        print_c("AI: ", Colours.BLUE + Colours.BOLD, end='')
        res_text = ""
        try:
            for chunk in chat.send_msg(user_input, stream=True):
                print(chunk, end='')
                sys.stdout.flush()
                res_text += chunk
        except Exception as e:
            print_c(f"\n error: {e}", Colours.RED)
        print("\n")
        print_sep()
        print()
    print_c("\nexiting...", Colours.CYAN + Colours.BOLD)

if __name__ == "__main__":
    main()