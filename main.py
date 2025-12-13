import requests
import os
import json
import sys
from datetime import datetime
import curses
import textwrap

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
    
    def get_msgs(self):
        return self.convo_history

class UI:
    def __init__(self,stdscr,chat,chat_mgr):
        self.stdscr = stdscr
        self.chat = chat
        self.chat_mgr = chat_mgr
        self.current_res = ""
        self.input_buffer = ""
        self.status_msg = "Ready"
        self.scroll_offset = 0
        # curses stuff, AI helped me a bit with this as I'm quite new to curses
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)
        self.height, self.width = stdscr.getmaxyx()
        self.header_win = curses.newwin(3,self.width, 0,0)
        self.chats_win = curses.newwin(self.height - 6, self.width // 3, 3, 0)
        self.input_win = curses.newwin(3, self.width, self.height - 3,0)
        self.res_win = curses.newwin(self.height - 6, (self.width * 2) // 3, 3,self.width //3)
        self.res_win.scrollok(True)
        self.chats_win.scrollok(True)

    def draw_h(self):
        self.header_win.clear()
        self.header_win.attron(curses.color_pair(1) | curses.A_BOLD)
        title = "shellLLM"
        self.header_win.addstr(1, (self.width - len(title)) // 2, title)
        self.header_win.attroff(curses.color_pair(1) | curses.A_BOLD)
        self.header_win.border()
        self.header_win.refresh()
    
    def draw_chats(self):
        self.chats_win.clear()
        self.chats_win.border()
        title = f"chats ({len(self.chat_mgr.chats)})"
        self.chats_win.addstr(0,2,title,curses.color_pair(1) | curses.A_BOLD)
        y = 1
        max_y = self.chats_win.getmaxyx()[0] - 2
        for idx, chat_data in enumerate(self.chat_mgr.chats[:max_y]):
            if y >= max_y:
                break
            title = chat_data.get('title', 'New Chat')
            msg_count = len(chat_data.get('messages', []))
            if idx == self.chat_mgr.cur_chat_idx:
                color = curses.color_pair(2) | curses.A_BOLD
                prefix = "> "
            else:
                color = curses.color_pair(5)
                prefix = " "
            try:
                display_text = f"{prefix}{title}"
                self.chats_win.addstr(y,1,display_text[:self.width // 3 - 3], color)
                if msg_count > 0:
                    self.chats_win.addstr(f"({msg_count})", curses.color_pair(5) | curses.A_DIM)
                y += 1
            except curses.error:
                pass
            self.chats_win.refresh()
        try:
            controls = "[n]ew [d]elete"
            self.chats_win.addstr(max_y + 1, 2, controls, curses.color_pair(4) | curses.A_DIM)
        except curses.error:
            pass

    def draw_res(self):
        self.res_win.clear()
        self.res_win.border()
        title = " response"
        self.res_win.addstr(0,2,title,curses.color_pair(3)|curses.A_BOLD)
        if self.current_res:
            max_width = (self.width * 2)//3 - 4
            lines = []
            for pg in self.current_res.split('\n'):
                if pg:
                    wrapped = textwrap.wrap(pg,width=max_width)
                    lines.extend(wrapped)
                else:
                    lines.append("")
            max_y = self.res_win.getmaxyx()[0] -2
            start = self.scroll_offset
            end = min(start + max_y, len(lines))
            y = 1
            for line in lines[start:end]:
                if y >= max_y + 1:
                    break
                try:
                    self.res_win.addstr(y,2,line[:max_width],curses.color_pair(5))
                    y += 1
                except curses.error:
                    pass
            if len(lines) > max_y:
                scroll_info = f" {start+1}-{end}/{len(lines)} "
                try:
                    self.res_win.addstr(0,self.res_win.getmaxyx()[1] - len(scroll_info) -2, scroll_info, curses.color_pair(4) | curses.A_DIM)
                except curses.error:
                    pass
        else:
            try:
                self.res_win.addstr(2,2,"waiting for input...",curses.color_pair(5)|curses.A_DIM)
            except curses.error:
                pass
        self.res_win.refresh()

    
    def handle_scroll(self,direction):
        if not self.current_res:
            return
        max_width = (self.width * 2)//3 - 4
        lines = []
        for pg in self.current_res.split('\n'):
            if pg:
                wrapped = textwrap.wrap(pg,width=max_width)
                lines.extend(wrapped)
            else:
                lines.append(wrapped)
        max_y = self.res_win.getmaxyx()[0]-2
        max_scroll = max(0,len(lines) - max_y)
        if direction == 'up':
            self.scroll_offset = max(0,self.scroll_offset -1)
        elif direction == 'down':
            self.scroll_offset = min(max_scroll,self.scroll_offset + 1)
        elif direction == 'pageup':
            self.scroll_offset = max(0,self.scroll_offset - max_y)
        elif direction == 'pagedown':
            self.scroll_offset = min(max_scroll,self.scroll_offset + max_y)
        elif direction == 'home':
            self.scroll_offset = 0
        elif direction == 'end':
            self.scroll_offset = max_scroll
        self.draw_res()
    
    def draw_input(self):
        self.input_win.clear()
        self.input_win.border()
        try:
            self.input_win.addstr(0,2,f"{self.status_msg} ", curses.color_pair(4))
        except curses.error:
            pass
        prompt = "You: "
        try:
            self.input_win.addstr(1,2,prompt,curses.color_pair(2) | curses.A_BOLD)
            self.input_win.addstr(self.input_buffer[:self.width - len(prompt) - 4])
        except curses.error:
            pass
        self.input_win.refresh()
    
    def refresh_all(self):
        self.draw_h()
        self.draw_chats()
        self.draw_res()
        self.draw_input()
    
    def get_input(self):
        self.input_buffer = ""
        self.status_msg = "type message (enter to send, ctrl+c to quit)"
        self.draw_input()
        curses.echo()
        curses.curs_set(1)
        try:
            self.input_win.move(1,7)
            self.input_buffer = self.input_win.getstr(1,7,self.width - 10).decode('utf-8').strip()
        except KeyboardInterrupt:
            return None
        finally:
            curses.noecho()
            curses.curs_set(0)
        return self.input_buffer
    
    def show_streaming(self,msg_gen):
        self.current_res = ""
        self.status_msg = "AI is responding..."
        for chunk in msg_gen:
            self.current_res += chunk
            self.draw_res()
            self.draw_input()
        self.status_msg = "Ready"
        self.draw_input()
    
    def handle_sinput(self):
        #self.status_msg = "arrow keys: navigate chats, ESC: exit nav mode, enter: select, n: new, d: delete, q: quit"
        #self.draw_input()
        key = self.stdscr.getch()
        if key == curses.KEY_UP:
            if self.chat_mgr.cur_chat_idx > 0:
                self.chat_mgr.cur_chat_idx -= 1
                self.chat_mgr.save_chats()
                return 'switch'
        elif key == curses.KEY_DOWN:
            if self.chat_mgr.cur_chat_idx < len(self.chat_mgr.chats) -1:
                self.chat_mgr.cur_chat_idx += 1
                self.chat_mgr.save_chats()
                return 'switch'
        elif key == ord('j') or key == ord('J'):
            self.handle_scroll('down')
            return 'scroll'
        elif key == ord('k') or key == ord('K'):
            self.handle_scroll('up')
            return 'scroll'
        elif key == ord('w') or key == ord('W'):
            self.handle_scroll('pageup')
            return 'scroll'
        elif key == ord('s') or key == ord('S'):
            self.handle_scroll('pagedown')
            return 'scroll'
        elif key == ord('g'):
            self.handle_scroll('home')
            return 'scroll'
        elif key == ord('G'):
            self.handle_scroll('end')
            return 'scroll'
        elif key == ord('n'):
            return 'new'
        elif key == ord('d'):
            return 'delete'
        elif key == 27:
            return 'exit_nav'
        elif key == ord('q'):
            return 'quit'
        return None

class chatMgr:
    def __init__(self):
        self.chats = []
        self.cur_chat_idx = 0
        self.chats_file = os.path.join(os.path.dirname(__file__), 'chats.json')
        self.load_chats()
    
    def load_chats(self):
        if os.path.exists(self.chats_file):
            try:
                with open(self.chats_file, 'r') as f:
                    data = json.load(f)
                    self.chats = data.get('chats',[])
                    self.cur_chat_idx = data.get('cur',0)
            except:
                pass
        if not self.chats:
            self.chats = [{"title": "New Chat", "messages": [], "timestamp": datetime.now().isoformat()}]
    
    def save_chats(self):
        try:
            with open(self.chats_file, 'w') as f:
                json.dump({'chats': self.chats, 'current': self.cur_chat_idx}, f,indent=2)
        except:
            pass
    
    def get_cur_chat(self):
        return self.chats[self.cur_chat_idx]
    
    def upd_cur_chat(self,msgs):
        chat = self.chats[self.cur_chat_idx]
        chat['messages'] = msgs
        for msg in msgs:
            if msg['role'] == 'user':
                content = msg['content'][:30] + "..." if len(msg['content']) > 30 else msg['content']
                chat['title'] = content
                break
        chat['timestamp'] = datetime.now().isoformat()
        self.save_chats()
    
    def new_chat(self):
        self.chats.insert(0,{"title": "New Chat", "messages": [], "timestamp": datetime.now().isoformat()})
        self.cur_chat_idx = 0
        self.save_chats()
    
    def switch_chat(self,idx):
        if 0 <= idx < len(self.chats):
            self.cur_chat_idx = idx
            self.save_chats()
            return True
        return False

    def del_cur_chat(self):
        if len(self.chats) > 1:
            del self.chats[self.cur_chat_idx]
            self.cur_chat_idx = min(self.cur_chat_idx,len(self.chats)-1)
            self.save_chats()
            return True
        return False
    

def main_tui(stdscr):
    curses.curs_set(0)
    stdscr.clear()
    load_env()
    api_key = os.environ.get("API_KEY")
    if not api_key:
        stdscr.addstr(0,0,"error: API_KEY not set in .env file")
        stdscr.addstr(1,0,"press any key to exit...")
        stdscr.getch()
        return
    try:
        chat_mgr = chatMgr()
        chat = mainChat(api_key, model="openai/gpt-5.1")
        curr_chat = chat_mgr.get_cur_chat()
        chat.convo_history = curr_chat.get('messages', [])
        ui = UI(stdscr,chat, chat_mgr)
    except Exception as e:
        stdscr.addstr(0,0,f"error: {str(e)}")
        stdscr.addstr(1,0,f"press any key to exit...")
        stdscr.getch()
        return
    ui.refresh_all()
    icm = False ## icm = in chat mode
    while True:
        if icm:
            ui.status_msg = "up/down arrow keys: nav chats, j/k: scroll, w/s: page, g/G: top/bottom, n: new, d: del, ESC: exit, q: quit"
            ui.refresh_all()
            action = ui.handle_sinput()
            if action == 'switch':
                curr_chat = chat_mgr.get_cur_chat()
                chat.convo_history = curr_chat.get('messages',[])
                ui.current_res = ""
                for msg in reversed(chat.convo_history):
                    if msg['role'] == 'assistant':
                        ui.current_res = msg['content']
                        break
                ui.scroll_offset = 0
                ui.status_msg = "switched chat"
                ui.refresh_all()
            elif action == 'new':
                chat_mgr.new_chat()
                chat.convo_history = []
                ui.current_res = ""
                ui.scroll_offset = 0
                ui.status_msg = "new chat created"
                ui.refresh_all()
            elif action == 'delete':
                if chat_mgr.del_cur_chat():
                    curr_chat = chat_mgr.get_cur_chat()
                    chat.convo_history = curr_chat.get('messages',[])
                    ui.current_res = ""
                    ui.scroll_offset = 0
                    ui.status_msg = "chat deleted"
                else:
                    ui.status_msg = "cannot/couldn't delete last chat"
                ui.refresh_all()
            elif action == 'exit_nav':
                icm = False
                ui.status_msg = "exited nav mode"
                ui.refresh_all()
            elif action == 'scroll':
                ui.refresh_all()
            elif action == 'quit':
                break
            continue

        ui.stdscr.nodelay(False)
        user_input = ui.get_input()
        if user_input is None:
            break
        if not user_input:
            continue
        if user_input.lower() in ['quit','exit']:
            break
        if user_input.lower() == 'nav':
            icm = True
            ui.status_msg = "nav mode - use arrow keys"
            ui.refresh_all()
            continue
        if user_input.lower() == 'clear':
            chat.clear_hist()
            ui.current_res = ""
            ui.scroll_offset = 0
            ui.status_msg = "history cleared"
            ui.refresh_all()
            continue
        if user_input.lower() == 'n':
            chat_mgr.new_chat()
            chat.convo_history = []
            ui.current_res = ""
            ui.scroll_offset = 0
            ui.status_msg = "new chat created"
            ui.refresh_all()
            continue
        if user_input.lower() == 'd':
            if chat_mgr.del_cur_chat():
                curr_chat = chat_mgr.get_cur_chat()
                chat.convo_history = curr_chat.get('messages',[])
                ui.current_res = ""
                ui.scroll_offset = 0
                ui.status_msg = "chat deleted"
            else:
                ui.status_msg = "cannot/couldn't delete last chat"
            ui.refresh_all()
            continue
        try:
            res_gen = chat.send_msg(user_input,stream=True)
            ui.show_streaming(res_gen)
            ui.scroll_offset = 0
            chat_mgr.upd_cur_chat(chat.convo_history)
            ui.refresh_all()
        except Exception as e:
            ui.status_msg = f"error: {str(e)}"
            ui.draw_input()
            curses.napms(2000)

def main():
    try:
        curses.wrapper(main_tui)
    except KeyboardInterrupt:
        pass
    print("\nexiting shellLLM...")

if __name__ == "__main__":
    main()