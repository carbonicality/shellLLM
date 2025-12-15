import requests
import os
import json
import sys
from datetime import datetime
import curses
import textwrap
import base64
import mimetypes

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
        self.attached_files = []
    
    def send_msg(self,user_msg,stream=True):
        if self.attached_files:
            for f in self.attached_files:
                if f['type'] == 'text':
                    file_context = f"\n\n--- file: {f['name']} --- \n{f['content']}\n--- end of {f['name']} --- \n"
                    user_msg = file_context + user_msg
            has_imgs = any(f['type'] == 'image' for f in self.attached_files)
            if has_imgs:
                content_parts = [{"type":"text","text":user_msg}]
                for f in self.attached_files:
                    if f['type'] == 'image':
                        content_parts.append({
                            "type":"image_url",
                            "image_url": {
                                "url": f"data:{f['mime_type']};base64,{f['content']}"
                            }
                        })
                self.convo_history.append({
                    "role": "user",
                    "content": content_parts
                })
            else:
                self.convo_history.append({
                    "role": "user",
                    "content": user_msg
                })
            self.clear_attch()
        else:
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
    
    def regen_last(self,stream=True):
        if len(self.convo_history) < 2:
            return None
        if self.convo_history[-1]['role'] == 'assistant':
            self.convo_history.pop()
        if stream:
            return self._stream_res()
        else:
            return self._get_res()

    def attach_file(self,filepath):
        file_type,mime_type = fileHandler.get_file_type(filepath)
        if file_type == 'unknown':
            return False, "unsupported file type :("
        if file_type == 'text':
            content = fileHandler.read_tfile(filepath)
            if content is None:
                return False, "couldn't read file"
            self.attached_files.append({
                'type': 'text',
                'filepath': filepath,
                'content': content,
                'name': os.path.basename(filepath)
            })
            return True, f"attached text file: {os.path.basename(filepath)}"
        elif file_type == 'image':
            content = fileHandler.read_img_file(filepath)
            if content is None:
                return False, "couldn't read image"
            self.attached_files.append({
                'type': 'image',
                'filepath': filepath,
                'content': content,
                'mime_type': mime_type,
                'name': os.path.basename(filepath)
            })
            return True, f"attached image: {os.path.basename(filepath)}"
        return False, "unknown error" # uh oh.
    
    def clear_attch(self):
        self.attached_files = []
    
    def get_attch_sum(self):
        if not self.attached_files:
            return "no files attached"
        summary = []
        for f in self.attached_files:
            summary.append(f"{f['name']} ({f['type']})")
        return ", ".join(summary)

class UI:
    def __init__(self,stdscr,chat,chat_mgr):
        self.stdscr = stdscr
        self.chat = chat
        self.chat_mgr = chat_mgr
        self.current_res = ""
        self.input_buffer = ""
        self.status_msg = "Ready"
        self.scroll_offset = 0

        self.show_stats = False
        self.v_msg_idx = -1

        self.show_help = False
        self.show_model_sel = False
        self.model_in_buffer = ""

        self.show_file_atch = False 
        self.file_path_buffer = ""

        self.show_search = False
        self.search_in_buffer = ""
        self.search_results = []
        # curses stuff, AI helped me a bit with this as I'm quite new to curses
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_MAGENTA,curses.COLOR_BLACK)
        self.height, self.width = stdscr.getmaxyx()

        self.header_win = curses.newwin(3,self.width, 0,0)
        self.chats_win = curses.newwin(self.height - 6, self.width // 3, 3, 0)
        self.input_win = curses.newwin(3, self.width, self.height - 3,0)
        self.res_win = curses.newwin(self.height - 6, (self.width * 2) // 3, 3,self.width //3)
        self.help_win = curses.newwin(30,60,(self.height - 30)//2, (self.width - 60)//2)
        self.model_win = curses.newwin(7,60,(self.height - 7) // 2, (self.width - 60)//2)
        self.search_win = curses.newwin(20,70,(self.height - 20) // 2, (self.width - 70)//2)
        self.file_win = curses.newwin(10,70,(self.height - 10) //2, (self.width - 70) // 2)
        self.stats_win = curses.newwin(20,70,(self.height - 20) //2, (self.width - 70) //2)

        self.res_win.scrollok(True)
        self.chats_win.scrollok(True)

    def draw_h(self):
        self.header_win.clear()
        self.header_win.attron(curses.color_pair(1) | curses.A_BOLD)
        title = "shellLLM"
        self.header_win.addstr(1,(self.width - len(title)) // 2,title)
        self.header_win.attroff(curses.color_pair(1) | curses.A_BOLD)
        mtxt = f"model: {self.chat.model}"
        try:
            self.header_win.addstr(1,self.width - len(mtxt) - 2, mtxt, curses.color_pair(4))
        except curses.error:
            pass
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

    def draw_model_sel(self):
        if not self.show_model_sel:
            return
        self.model_win.clear()
        self.model_win.border()
        self.model_win.attron(curses.color_pair(6) | curses.A_BOLD)
        self.model_win.addstr(0,2," select model ", curses.color_pair(6))
        self.model_win.attroff(curses.color_pair(6) | curses.A_BOLD)
        try:
            self.model_win.addstr(2,2,"enter model name:", curses.color_pair(5))
            self.model_win.addstr(3,2,"> ", curses.color_pair(2) | curses.A_BOLD)
            display_text = self.model_in_buffer if self.model_in_buffer else "openai/gpt-5.1"
            text_attr = curses.color_pair(5) if self.model_in_buffer else curses.color_pair(5) | curses.A_DIM
            self.model_win.addstr(3,4,display_text[:52],text_attr)
            self.model_win.addstr(5,2,"press ENTER to confirm, ESC to cancel", curses.color_pair(4) | curses.A_DIM)
        except curses.error:
            pass
        self.model_win.refresh()
    
    def get_model_in(self):
        self.model_in_buffer = ""
        curses.curs_set(1)
        self.model_win.nodelay(False)
        try:
            while True:
                self.model_win.move(3,4)
                self.model_win.addstr(3,4," " * 52)
                self.model_win.move(3,4)
                if self.model_in_buffer:
                    self.model_win.addstr(3,4,self.model_in_buffer[:52],curses.color_pair(5))
                else:
                    self.model_win.addstr(3,4,"openai/gpt-5.1",curses.color_pair(5) | curses.A_DIM)
                cursor_pos = min(len(self.model_in_buffer),52)
                self.model_win.move(3,4 + cursor_pos)
                self.model_win.refresh()
                ch = self.model_win.getch()
                if ch == 27:
                    return None
                elif ch == 10 or ch == curses.KEY_ENTER:
                    return self.model_in_buffer if self.model_in_buffer else None
                elif ch == curses.KEY_BACKSPACE or ch == 127 or ch == 8:
                    if self.model_in_buffer:
                        self.model_in_buffer = self.model_in_buffer[:-1]
                elif 32 <= ch <= 126:
                    if len(self.model_in_buffer) < 52:
                        self.model_in_buffer += chr(ch)
        except KeyboardInterrupt:
            return None
        finally:
            curses.curs_set(0)
            self.model_in_buffer = ""
    
    def draw_search(self):
        if not self.show_search:
            return
        self.search_win.clear()
        self.search_win.border()
        self.search_win.attron(curses.color_pair(6) | curses.A_BOLD)
        self.search_win.addstr(0,2," search chats", curses.color_pair(6))
        self.search_win.attroff(curses.color_pair(6) | curses.A_BOLD)
        try:
            self.search_win.addstr(2,2,"search for:", curses.color_pair(5))
            self.search_win.addstr(3,2,"> ",curses.color_pair(2) | curses.A_BOLD)
            display_text = self.search_in_buffer if self.search_in_buffer else "type to search..."
            text_attr = curses.color_pair(5) if self.search_in_buffer else curses.color_pair(5) | curses.A_DIM
            self.search_win.addstr(3,4,display_text[:62],text_attr)

            if self.search_results:
                self.search_win.addstr(5,2,f"found {len(self.search_results)} result(s):", curses.color_pair(4))
                max_results = 10
                for i, (chat_idx,snippet) in enumerate(self.search_results[:max_results]):
                    if i + 7 >= 19:
                        break
                    chat_tl = self.chat_mgr.chats[chat_idx].get('title', 'New Chat')
                    result_ln = f"{i+1}. {chat_tl[:30]}"
                    try:
                        self.search_win.addstr(i+7,2,result_ln[:66],curses.color_pair(2))
                    except curses.error:
                        pass
                if len(self.search_results) > max_results:
                    self.search_win.addstr(17,2,f"... and {len(self.search_results) - max_results} more",curses.color_pair(4) | curses.A_DIM)
            elif self.search_in_buffer:
                self.search_win.addstr(5,2,"no results found",curses.color_pair(4) | curses.A_DIM)
            self.search_win.addstr(18,2,"ENTER to search, 1-9 to jump to result, ESC to cancel", curses.color_pair(4) | curses.A_DIM)
        except curses.error:
            pass
        self.search_win.refresh()
    
    def get_search_in(self):
        self.search_in_buffer = ""
        self.search_results = []
        curses.curs_set(1)
        self.search_win.nodelay(False)
        try:
            while True:
                self.search_win.move(3,4)
                self.search_win.addstr(3,4," " * 62)
                self.search_win.move(3,4)
                if self.search_in_buffer:
                    self.search_win.addstr(3,4,self.search_in_buffer[:62],curses.color_pair(5))
                else:
                    self.search_win.addstr(3,4,"type to search...",curses.color_pair(5) | curses.A_DIM)
                cursor_pos = min(len(self.search_in_buffer),62)
                self.search_win.move(3,4+cursor_pos)
                self.search_win.refresh()
                ch = self.search_win.getch()
                if ch == 27:
                    return None
                elif ch == 10 or ch == curses.KEY_ENTER:
                    if self.search_in_buffer:
                        self.perf_search()
                        self.draw_search()
                elif ch >= ord('1') and ch <= ord('9'):
                    result_num = ch - ord('1')
                    if result_num < len(self.search_results):
                        return self.search_results[result_num][0]
                elif ch == curses.KEY_BACKSPACE or ch == 127 or ch == 8:
                    if self.search_in_buffer:
                        self.search_in_buffer = self.search_in_buffer[:-1]
                        if self.search_in_buffer:
                            self.perf_search()
                        else:
                            self.search_results = []
                        self.draw_search()
                elif 32 <= ch <= 126:
                    if len(self.search_in_buffer) < 62:
                        self.search_in_buffer += chr(ch)
                        self.perf_search()
                        self.draw_search()
        except KeyboardInterrupt:
            return None
        finally:
            curses.curs_set(0)
            self.search_in_buffer = ""
            self.search_results = []
    
    def perf_search(self):
        query = self.search_in_buffer.lower()
        self.search_results = []
        for idx,chat in enumerate(self.chat_mgr.chats):
            title = chat.get('title', '').lower()
            if query in title:
                self.search_results.append((idx,title[:50]))
                continue
            for msg in chat.get('messages', []):
                content = msg.get('content','').lower()
                if query in content:
                    match_pos = content.find(query)
                    start = max(0,match_pos - 20)
                    end = min(len(content),match_pos + 30)
                    snippet = content[start:end]
                    self.search_results.append((idx,snippet))
                    break
    
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
        self.stdscr.clear()
        self.stdscr.noutrefresh()
        self.draw_h()
        self.draw_chats()
        self.draw_res()
        self.draw_input()
        if self.show_help:
            self.draw_help()
        if self.show_model_sel:
            self.draw_model_sel()
        if self.show_search:
            self.draw_search()
        curses.doupdate()
        if self.show_stats:
            self.draw_stats()
        if self.show_file_atch:
            self.draw_file_atch()
    
    def get_input(self):
        self.input_buffer = ""
        self.status_msg = "type a message and press enter, or type '::nav' to enter navigation mode. type '::help' for help."
        max_in_width = self.width - 10
        view_offset = 0
        auto_scroll = True
        curses.curs_set(1)
        try:
            while True:
                cursor_pos = len(self.input_buffer)
                vis_start = view_offset
                vis_end = view_offset + max_in_width
                vis_txt = self.input_buffer[vis_start:vis_end]
                self.input_win.clear()
                self.input_win.border()
                try:
                    self.input_win.addstr(0,2,f"{self.status_msg} ",curses.color_pair(4))
                except curses.error:
                    pass
                prompt = "You: "
                try:
                    self.input_win.addstr(1,2,prompt,curses.color_pair(2)|curses.A_BOLD)
                    self.input_win.addstr(1,7,vis_txt)
                    if view_offset > 0:
                        self.input_win.addstr(1,6,"<",curses.color_pair(4))
                    if len(self.input_buffer) > vis_end:
                        self.input_win.addstr(1,7 + len(vis_txt), ">",curses.color_pair(4))
                except curses.error:
                    pass
                cursor_scr_pos = min(7 + len(vis_txt), 7 + max_in_width - 1)
                self.input_win.move(1,cursor_scr_pos)
                self.input_win.refresh()
                ch = self.input_win.getch()
                if ch == 10 or ch == curses.KEY_ENTER:
                    break
                elif ch == 27:
                    self.input_win.nodelay(True)
                    next_ch = self.input_win.getch()
                    if next_ch == -1:
                        self.input_win.nodelay(False)
                        return None
                    elif next_ch == ord('['):
                        third_ch = self.input_win.getch()
                        self.input_win.nodelay(False)
                        if third_ch == ord('D'): # left arrow
                            view_offset = max(0,view_offset - 10)
                            auto_scroll = False
                        elif third_ch == ord('C'): # right arrow
                            max_offset = max(0,len(self.input_buffer) - max_in_width)
                            view_offset = min(view_offset + 10,max_offset)
                            if view_offset >= max_offset:
                                auto_scroll = True
                        continue
                    else:
                        self.input_win.nodelay(False)
                        continue
                elif ch == curses.KEY_BACKSPACE or ch == 127 or ch == 8:
                    if len(self.input_buffer) > 0:
                        self.input_buffer = self.input_buffer[:-1]
                        if auto_scroll:
                            view_offset = max(0,len(self.input_buffer) - max_in_width)
                elif 32 <= ch <= 126:
                    self.input_buffer += chr(ch)
                    if auto_scroll:
                        if len(self.input_buffer) > max_in_width:
                            view_offset = len(self.input_buffer) - max_in_width
            return self.input_buffer.strip()
        except KeyboardInterrupt:
            return None
        finally:
            curses.curs_set(0)
         
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
                self.v_msg_idx = -1
                return 'switch'
        elif key == curses.KEY_DOWN:
            if self.chat_mgr.cur_chat_idx < len(self.chat_mgr.chats) -1:
                self.chat_mgr.cur_chat_idx += 1
                self.chat_mgr.save_chats()
                self.v_msg_idx = -1
                return 'switch'
        elif key == ord('u') or key == ord('U'):
            self.nav_msgs('up')
            return 'msg_nav'
        elif key == ord('p') or key == ord('P'):
            self.nav_msgs('down')
            return 'msg_nav'
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
        elif key == ord('r') or key == ord('R'):
            return 'regen'
        elif key == ord('i') or key == ord('I'):
            return 'toggle_stats'
        elif key == ord('h') or key == ord('H'):
            self.show_help = not self.show_help
            return 'toggle_help'
        elif key == ord('n'):
            return 'new'
        elif key == ord('f') or key == ord('F'):
            return 'toggle_search'
        elif key == ord('m') or key == ord('M'):
            return 'toggle_model'
        elif key == ord('d'):
            return 'delete'
        elif key == ord('a') or key == ord('A'):
            return 'attach_file'
        elif key == 27:
            return 'exit_nav'
        elif key == ord('q'):
            return 'quit'
        return None
    
    def draw_help(self):
        if not self.show_help:
            return
        self.help_win.clear()
        self.help_win.border()
        self.help_win.attron(curses.color_pair(6) | curses.A_BOLD)
        self.help_win.addstr(0,2," HELP - press 'h' to toggle", curses.color_pair(6))
        self.help_win.attroff(curses.color_pair(6) | curses.A_BOLD)
        help_txt = [ # fancy shmancy am i right
            "normal mode:",
            " - type your message and press enter",
            " - type '::nav' to enter navigation mode",
            " - type '::clear' to clear chat history",
            " - type '::model' to change model",
            " - type '::n' to make a new chat",
            " - type '::d' to delete the selected chat",
            " - type '::search' or '::search <query>' to search",
            " - type '::regen' to regenerate last response",
            " - type '::stats' to view convo stats (wrapped fr)",
            " - type '::attach' or '::a' to attach a file",
            " - type '::clear-attach' to clear attachments",
            " - type '::help' for help",
            "",
            "navigation mode:",
            " - up/down arrow keys: navigate chats",
            " - j/k keys: scroll response by line",
            " - w/s keys: scroll response by page",
            " - g/G keys: jump to top/bottom of response",
            " - n: new chat",
            " - m: change model",
            " - d: delete selected chat",
            " - ESC: exit nav mode",
            " - h: show help window",
            " - f: search through chats",
            " - a: attach file",
            " - r: regenerate last response",
            " - i: show convo stats (wrapped fr)",
            " - u/p keys: navigate through response history",
            " - q: quit shellLLM"
        ]
        for i, line in enumerate(help_txt, start=1):
            if i > 28:
                break
            try:
                if line and not line.startswith(" "):
                    self.help_win.addstr(i,2,line,curses.color_pair(2)|curses.A_BOLD)
                else:
                    self.help_win.addstr(i,2,line,curses.color_pair(5))
            except curses.error:
                pass
        self.help_win.refresh()
    
    def draw_stats(self):
        if not self.show_stats:
            return
        self.stats_win.clear()
        self.stats_win.border()
        self.stats_win.attron(curses.color_pair(6) | curses.A_BOLD)
        self.stats_win.addstr(0,2," conversation stats (wrapped?) ",curses.color_pair(6))
        self.stats_win.attroff(curses.color_pair(6) | curses.A_BOLD)
        t_chats = len(self.chat_mgr.chats)
        t_msgs = sum(len(chat.get('messages',[])) for chat in self.chat_mgr.chats)
        t_user_msgs = sum(len([m for m in chat.get('messages',[]) if m['role'] == 'user']) for chat in self.chat_mgr.chats)
        t_ai_msgs = sum(len([m for m in chat.get('messages',[]) if m['role'] == 'assistant']) for chat in self.chat_mgr.chats)
        avg_msgs = t_msgs / t_chats if t_chats > 0 else 0
        most_active = max(self.chat_mgr.chats,key=lambda c:len(c.get('messages',[])), default=None)
        most_active_title = most_active.get('title','N/A')[:40] if most_active else 'N/A'
        most_active_count = len(most_active.get('messages',[])) if most_active else 0
        sorted_chats = sorted([c for c in self.chat_mgr.chats if c.get('timestamp')],key=lambda c: c.get('timestamp',''))
        oldest = sorted_chats[0] if sorted_chats else None
        newest = sorted_chats[-1] if sorted_chats else None
        stats_txt = [
            f"total chats: {t_chats}",
            f"total messages: {t_msgs}",
            f" - user messages: {t_user_msgs}",
            f" - AI messages: {t_ai_msgs}",
            f"average messages per chat: {avg_msgs:.1f}",
            "",
            f"most active chat:",
            f"  {most_active_title}",
            f"  ({most_active_count} messages)",
            "",
            f"current model: {self.chat.model}"
        ]
        if oldest:
            oldest_date = oldest.get('timestamp','')[:10]
            stats_txt.extend([
                "",
                f"oldest chat: {oldest_date}"
            ])
        if newest and newest != oldest:
            newest_date = newest.get('timestamp','')[:10]
            stats_txt.append(f"newest chat: {newest_date}")
        for i, line in enumerate(stats_txt,start=2):
            if i > 17:
                break
            try:
                if ':' in line and not line.startswith(' '):
                    parts = line.split(':',1)
                    self.stats_win.addstr(i,2,parts[0] + ':',curses.color_pair(2) | curses.A_BOLD)
                    if len(parts) > 1:
                        self.stats_win.addstr(parts[1],curses.color_pair(5))
                else:
                    self.stats_win.addstr(i,2,line,curses.color_pair(5))
            except curses.error:
                pass
        try:
            self.stats_win.addstr(18,2,"press any key to close", curses.color_pair(4) | curses.A_DIM)
        except curses.error:
            pass
        self.stats_win.refresh()
    
    def draw_file_atch(self):
        if not self.show_file_atch:
            return
        self.file_win.clear()
        self.file_win.border()
        self.file_win.attron(curses.color_pair(6) | curses.A_BOLD)
        self.file_win.addstr(0,2," attach file ",curses.color_pair(6))
        self.file_win.attroff(curses.color_pair(6) | curses.A_BOLD)
        try:
            self.file_win.addstr(2,2,"enter file path:",curses.color_pair(5))
            self.file_win.addstr(3,2,"> ",curses.color_pair(2) | curses.A_BOLD)
            display_text = self.file_path_buffer if self.file_path_buffer else "/path/to/file.txt"
            text_attr = curses.color_pair(5) if self.file_path_buffer else curses.color_pair(5) | curses.A_DIM
            self.file_win.addstr(3,4,display_text[:62],text_attr)
            if self.chat.attached_files:
                self.file_win.addstr(5,2,"attached files:",curses.color_pair(4))
                for i,f in enumerate(self.chats.attached_files[:3]):
                    self.file_win.addstr(6+i, 4,f"- {f['name']} ({f['type']})",curses.color_pair(2))
            self.file_win.addstr(8,2,"ENTER: attach, ESC: cancel, ctrl+c: clear all",curses.color_pair(4) | curses.A_DIM)
        except curses.error:
            pass
        self.file_win.refresh()
    
    def get_ftch_input(self):
        self.file_path_buffer = ""
        curses.curs_set(1)
        self.file_win.nodelay(False)
        try:
            while True:
                self.file_win.move(3,4)
                self.file_win.addstr(3,4," " * 62)
                self.file_win.move(3,4)
                if self.file_path_buffer:
                    self.file_win.addstr(3,4,self.file_path_buffer[:62],curses.color_pair(5))
                else:
                    self.file_win.addstr(3,4,"path/to/file.txt",curses.color_pair(5) | curses.A_DIM)
                cursor_pos = min(len(self.file_path_buffer),62)
                self.file_win.move(3,4 + cursor_pos)
                self.file_win.refresh()
                ch = self.file_win.getch()
                if ch == 27:
                    return None
                elif ch == 10 or ch == curses.KEY_ENTER:
                    if self.file_path_buffer:
                        exp_path = os.path.expanduser(self.file_path_buffer)
                        return exp_path
                    return None
                elif ch == 3:
                    self.chat.clear_attch()
                    self.file_path_buffer = ""
                    self.draw_file_atch()
                elif ch == curses.KEY_BACKSPACE or ch == 127 or ch == 8:
                    if self.file_path_buffer:
                        self.file_path_buffer = self.file_path_buffer[:-1]
                elif 32 <= ch <= 126:
                    if len(self.file_path_buffer) < 62:
                        self.file_path_buffer += chr(ch)
        except KeyboardInterrupt:
            return None
        finally:
            curses.curs_set(0)
            self.file_path_buffer = ""
    
    def nav_msgs(self,dir):
        if not self.chat.convo_history:
            return 
        ai_msgs = [(i,msg) for i,msg in enumerate(self.chat.convo_history) if msg['role'] == 'assistant']
        if not ai_msgs:
            return
        if self.v_msg_idx == -1:
            if dir == 'up':
                self.v_msg_idx = len(ai_msgs) - 1
        else:
            if dir == 'up':
                self.v_msg_idx = max(0,self.v_msg_idx - 1)
            elif dir == 'down':
                self.v_msg_idx += 1 
                if self.v_msg_idx >= len(ai_msgs):
                    self.v_msg_idx = -1
        if self.v_msg_idx == -1:
            for msg in reversed(self.chat.convo_history):
                if msg['role'] == 'assistant':
                    self.current_res = msg['content']
                    break
            self.status_msg = "viewing latest message"
        else:
            actual_idx,msg = ai_msgs[self.v_msg_idx]
            self.current_res = msg['content']
            self.status_msg = f"viewing message {self.v_msg_idx + 1}/{len(ai_msgs)} (up/down arrow keys to navigate)"
        self.scroll_offset = 0

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

class fileHandler:
    @staticmethod
    def read_tfile(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            return None
        
    @staticmethod
    def read_img_file(filepath):
        try:
            with open(filepath, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except FileNotFoundError:
            return None
    
    @staticmethod
    def get_file_type(filepath):
        mime_type, _ = mimetypes.guess_type(filepath)
        if mime_type:
            if mime_type.startswith('image/'):
                return 'image', mime_type
            elif mime_type.startswith('text/'):
                return 'text', mime_type
        if filepath.endswith(('.py', '.js', '.java', '.cpp', '.c', '.h', '.css', '.html', '.json', '.xml', '.yml', '.yaml', '.md', '.txt', '.log', '.sh', '.bash', '.rs', '.go', '.ts', '.jsx', '.tsx', '.vue', '.sql')): # i asked AI to give me all the file type extensions
            return 'text','text/plain'
        return 'unknown', None
    
def main_tui(stdscr):
    curses.curs_set(0)
    stdscr.clear()
    load_env()
    api_key = os.environ.get("API_KEY")
    if not api_key:
        stdscr.clear()
        stdscr.addstr(0,0,"API_KEY not found in environment or .env file", curses.A_BOLD)
        stdscr.addstr(2,0,"please enter your API key:")
        stdscr.addstr(3,0,"> ")
        stdscr.refresh()
        curses.echo()
        curses.curs_set(1)
        api_key_in = stdscr.getstr(3,2,100).decode('utf-8').strip()
        curses.noecho()
        curses.curs_set(0)
        if not api_key_in:
            stdscr.clear()
            stdscr.addstr(0,0,"no api key provided.")
            stdscr.addstr(1,0,"press any key to exit...")
            stdscr.getch()
            return
        os.environ["API_KEY"] = api_key_in
        api_key = api_key_in
        stdscr.clear()
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
            ui.status_msg = "nav mode - press h for help, esc to escape"
            ui.refresh_all()
            action = ui.handle_sinput()
            if action == 'switch':
                curr_chat = chat_mgr.get_cur_chat()
                chat.convo_history = curr_chat.get('messages',[])
                ui.current_res = ""
                ui.v_msg_idx = -1
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
                ui.show_help = False
                ui.show_model_sel = False
                ui.status_msg = "exited nav mode"
                ui.refresh_all()
            elif action == 'toggle_help':
                ui.refresh_all()
            elif action == 'toggle_model':
                ui.show_model_sel = True
                ui.refresh_all()
                new_mdl = ui.get_model_in()
                ui.show_model_sel = False 
                if new_mdl:
                    chat.model = new_mdl
                    ui.status_msg = f"model changed to: {new_mdl}"
                else:
                    ui.status_msg = "model change cancelled"
                ui.refresh_all()
            elif action == 'toggle_search':
                ui.show_search = True
                ui.refresh_all()
                sel_chat = ui.get_search_in()
                ui.show_search = False
                if sel_chat is not None:
                    chat_mgr.cur_chat_idx = sel_chat
                    curr_chat = chat_mgr.get_cur_chat()
                    chat.convo_history = curr_chat.get('messages',[])
                    ui.current_res = ""
                    for msg in reversed(chat.convo_history):
                        if msg['role'] == 'assistant':
                            ui.current_res = msg['content']
                            break
                    ui.scroll_offset = 0
                    ui.status_msg = f"jumped to chat: {curr_chat.get('title', 'New Chat')[:30]}"
                else:
                    ui.status_msg = "search cancelled"
                ui.refresh_all()
            elif action == 'msg_nav':
                ui.refresh_all()
            elif action == 'attach_file':
                ui.show_file_atch = True
                ui.refresh_all()
                filepath = ui.get_ftch_input()
                ui.show_file_atch = False
                if filepath:
                    success,message = chat.attach_file(filepath)
                    ui.status_msg = message
                else:
                    ui.status_msg = "file attachment cancelled"
                ui.refresh_all()
            elif action == 'regen':
                if len(chat.convo_history) >= 2:
                    ui.status_msg = "regenerating..."
                    ui.refresh_all()
                    try:
                        res_gen = chat.regen_last(stream=True)
                        if res_gen:
                            ui.show_streaming(res_gen)
                            ui.scroll_offset = 0
                            chat_mgr.upd_cur_chat(chat.convo_history)
                            ui.status_msg = "response generated"
                        else:
                            ui.status_msg = "no message to regenerate"
                    except Exception as e:
                        ui.status_msg = "no message to regenerate"
                    ui.refresh_all()
            elif action == 'toggle_stats':
                ui.show_stats = True
                ui.refresh_all()
                ui.stdscr.getch()
                ui.show_stats = False 
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
        if user_input.lower() == '::nav':
            icm = True
            ui.status_msg = "nav mode - use arrow keys"
            ui.refresh_all()
            continue
        if user_input.lower() == '::clear':
            chat.clear_hist()
            ui.current_res = ""
            ui.scroll_offset = 0
            ui.status_msg = "history cleared"
            ui.refresh_all()
            continue
        if user_input.lower() == '::n':
            chat_mgr.new_chat()
            chat.convo_history = []
            ui.current_res = ""
            ui.scroll_offset = 0
            ui.status_msg = "new chat created"
            ui.refresh_all()
            continue
        if user_input.lower() == '::d':
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
        if user_input.lower() == '::model':
            ui.show_model_sel = True
            ui.refresh_all()
            new_mdl = ui.get_model_in()
            ui.show_model_sel = False 
            if new_mdl:
                chat.model = new_mdl
                ui.status_msg = f"model changed to: {new_mdl}"
            else:
                ui.status_msg = "model change cancelled"
            ui.refresh_all()
            continue
        if user_input.lower().startswith('::search'):
            ui.show_search = True
            query_parts = user_input.split(' ',1)
            if len(query_parts) > 1:
                ui.search_in_buffer = query_parts[1]
                ui.perf_search()
            ui.refresh_all()
            sel_chat = ui.get_search_in()
            ui.show_search = False
            if sel_chat is not None:
                chat_mgr.cur_chat_idx = sel_chat
                curr_chat = chat_mgr.get_cur_chat()
                chat.convo_history = curr_chat.get('messages',[])
                ui.current_res = ""
                for msg in reversed(chat.convo_history):
                    if msg['role'] == 'assistant':
                        ui.current_res = msg['content']
                        break
                ui.scroll_offset = 0
                ui.status_msg = f"jumped to chat: {curr_chat.get('title', 'New Chat')[:30]}"
            else:
                ui.status_msg = "search cancelled"
            ui.refresh_all()
            continue
        if user_input.lower() in ['::attach', '::a']:
            ui.show_file_atch = True
            ui.refresh_all()
            filepath = ui.get_ftch_input()
            ui.show_file_atch = False
            if filepath:
                success,message = chat.attach_file(filepath)
                ui.status_msg = message
            else:
                ui.status_msg = "file attachment cancelled"
            ui.refresh_all()
            continue
        if user_input.lower() == '::clear-attach':
            chat.clear_attch()
            ui.status_msg = "cleared all attachments"
            ui.refresh_all()
            continue
        if user_input.lower() == '::help':
            ui.show_help = True
            ui.refresh_all()
            ui.stdscr.nodelay(False)
            ui.stdscr.getch()
            ui.show_help = False 
            ui.refresh_all()
            continue
        if user_input.lower() == '::regen':
            if len(chat.convo_history) >= 2:
                ui.status_msg = "regenerating..."
                ui.refresh_all()
                try:
                    res_gen = chat.regen_last(stream=True)
                    if res_gen:
                        ui.show_streaming(res_gen)
                        ui.scroll_offset = 0
                        chat_mgr.upd_cur_chat(chat.convo_history)
                        ui.status_msg = "response regenerated"
                    else:
                        ui.status_msg = "no message to regenerate"
                except Exception as e:
                    ui.status_msg = f"regeneration error: {str(e)}"
            else:
                ui.status_msg = "no message to regenerate"
            ui.refresh_all()
            continue
        if user_input.lower() == '::stats':
            ui.show_stats = True
            ui.refresh_all()
            ui.stdscr.nodelay(False)
            ui.stdscr.getch()
            ui.show_stats = False 
            ui.refresh_all()
            continue
        try:
            res_gen = chat.send_msg(user_input,stream=True)
            ui.show_streaming(res_gen)
            ui.scroll_offset = 0
            ui.v_msg_idx = -1
            chat_mgr.upd_cur_chat(chat.convo_history)
            ui.refresh_all()
        except Exception as e:
            ui.status_msg = f"error: {str(e)}"
            ui.draw_input()
            curses.napms(2000)

def main():
    # lil fix to stop a delay from switching from nav mode to normal mode
    os.environ.setdefault('ESCDELAY', '25')
    try:
        curses.wrapper(main_tui)
    except KeyboardInterrupt:
        pass
    print("\nexiting shellLLM...")

if __name__ == "__main__":
    main()