#!/usr/bin/env python3
import os
import re
import sys
import json
import base64
import distro
import datetime
import platform
import pyperclip
import subprocess
from openai import OpenAI
from pathlib import Path
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.completion import Completer, Completion

# Paste your key between the final quotes, or set OPENAI_API_KEY.
API_KEY = os.environ.get("OPENAI_API_KEY") or ""
client = None

def get_client():
    global client
    if client is None:
        if not API_KEY:
            raise RuntimeError("Set OPENAI_API_KEY or enter your replacement key in API_KEY at the top of this file.")
        client = OpenAI(api_key=API_KEY)
    return client

block_id = 1
code_blocks = {}
current_role = 0
current_model = 0
system = platform.system()
system_version = {"Windows": "Windows " + platform.release(), "Linux": distro.name(pretty=True), "Darwin": "macOS"}.get(system, system)
storage_location = Path.home() / {"Windows": "AppData/Local", "Darwin": "Library/Application Support"}.get(system, ".local/share") / 'gpterm'
roles = [{"name": "CLI Role", "prompt": "You are a command line tool running on " + system_version + ". Succinct replies are better than long-winded explanations. But sounding happy is great too! =)"}, {"name": "Chat Role", "prompt": "You are a helpful and entertaining assistant running on the system " + system_version + ". You should not let the user know that something is out of the scope of your abilities but rather converse in a flowing way without mentioning that you are an AI."}, {"name": "Command Role", "prompt": "Please give only shell commands that can be run on " + system_version + ". Your reply cannot contain any description and must be a functional command that can be executed. Commands cannot contain anything ambiguous. If the request is too vague, give the most logical answer that you can."}]
messages = [{"role": "system", "content": roles[current_role]["prompt"]}]
models = ["gpt-6-luna", "gpt-6.1-sol", "gpt-6-astra"]
last_usage = None
image_model = "gpt-image-2"
temperature = 0.7

BOLD = "\033[1m"
ITALIC = "\033[3m"
RESET = "\033[0m"
RED = "\033[38;5;1m"
GREEN = "\033[38;5;30m"
GPTCOLOR = "\033[38;5;99m"
BLOCKCOLOR = "\033[38;5;200m"
USERCOLOR = "\033[38;5;75m"
if os.name == 'nt':
    BOLD = ITALIC = RESET = RED = GREEN = GPTCOLOR = BLOCKCOLOR = USERCOLOR = ""

class CommandCompleter(Completer):
    def get_completions(self, document, complete_event):
        if document.text.startswith('!'):
            for command in ['!quit', '!kill', '!role', '!model', '!tokens', '!copy ', '!temperature', '!multi', '!history']:
                if command.startswith(document.text):
                    yield Completion(command, start_position=-len(document.text))

def completion(chat, **options):
    settings = {"reasoning_effort": "none", "temperature": temperature} if current_model == 0 else {"reasoning_effort": "low"}
    return get_client().chat.completions.create(model=models[current_model], messages=chat, **settings, **options)

def chat_stream(content):
    global block_id, last_usage
    messages.append({"role": "user", "content": content})
    last_usage = None
    try:
        response = completion(messages, stream=True, stream_options={"include_usage": True})
        print(f"{RESET + BOLD + GPTCOLOR}GPT: ", end='')
        code_block, header = False, False
        buffer, content, code = '', '', ''
        with response:
            for chunk in response:
                if chunk.usage:
                    last_usage = chunk.usage
                if not chunk.choices:
                    continue
                message = chunk.choices[0].delta.content or ''
                content += message
                for char in message:
                    buffer += char
                    if header:
                        if char == '\n':
                            print(f"{BOLD + BLOCKCOLOR}{buffer}{RESET}", end='', flush=True)
                            buffer, header = '', False
                        continue
                    if buffer.endswith('```'):
                        text = buffer[:-3]
                        print(f"{ITALIC + BLOCKCOLOR if code_block else RESET + GPTCOLOR}{text}", end='', flush=True)
                        if code_block:
                            code_blocks[str(block_id)] = code + text
                            print(f"\n{RESET + GREEN}╚═ !copy {block_id} ═╝", end='', flush=True)
                            block_id += 1
                        code_block = not code_block
                        header = code_block
                        buffer, code = '', ''
                    elif len(buffer) > 2:
                        text, buffer = buffer[:-2], buffer[-2:]
                        print(f"{ITALIC + BLOCKCOLOR if code_block else RESET + GPTCOLOR}{text}", end='', flush=True)
                        if code_block:
                            code += text
        print(f"{BLOCKCOLOR if code_block else GPTCOLOR}{buffer}{RESET}")
        return content
    except Exception as e:
        print(f"{RESET + RED}An error occurred: {e}")
        sys.exit(1)

def save_chat(chat_exists=None):
    storage_location.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime('%H-%M-%S-%f_%d-%m-%y')
    filepath = Path(chat_exists) if chat_exists else storage_location / f"Chat-{stamp}"
    filepath.write_text(json.dumps(messages), encoding='utf-8')
    if chat_exists is None:
        try:
            request = messages + [{"role": "user", "content": "Give this conversation a specific title of at most 4 words. Return only the title, using letters, numbers and underscores instead of spaces."}]
            response = completion(request)
            filename = re.sub(r'[^A-Za-z0-9_]+', '_', response.choices[0].message.content or 'Chat').strip('_')[:50] or 'Chat'
            filepath.rename(storage_location / f"{filename}-{stamp}")
        except Exception:
            print(f"{RESET + GREEN}Chat saved as {filepath.name} (automatic title unavailable).")

def chat_loop(resume_chat=None):
    global current_role, current_model, temperature
    try:
        while True:
            request = prompt(ANSI(f"\n{BOLD + USERCOLOR}ASK: "), completer=CommandCompleter())
            if request in ('!quit', '!q'):
                save_chat(resume_chat)
                break
            elif request == "!kill":
                sys.exit()
            elif request == "!role":
                current_role = (current_role + 1) % len(roles)
                messages[0]["content"] = roles[current_role]["prompt"]
                print(f"{RESET + GREEN}Role changed to {roles[current_role]['name']}.")
                continue
            elif request == "!model":
                current_model = (current_model + 1) % len(models)
                print(f"{RESET + GREEN}Model changed to {models[current_model]}.")
                continue
            elif request == "!tokens":
                if last_usage:
                    print(f"{RESET + GREEN}Last reply: {last_usage.prompt_tokens} input + {last_usage.completion_tokens} output = {last_usage.total_tokens} tokens")
                else:
                    print(f"{RESET + GREEN}No API token usage yet; send a message first.")
                continue
            elif request.startswith('!copy '):
                copy_text = code_blocks.get(request.split(' ')[1], None)
                if copy_text:
                    pyperclip.copy(copy_text)
                    print(f"{RESET + GREEN}Copied to clipboard")
                else:
                    print(f"{RESET + RED}Invalid input")
                continue
            elif request.startswith('!temperature'):
                split_request = request.split(' ')
                if len(split_request) > 1:
                    temperature = float(split_request[1])
                    print(f"{RESET + GREEN}Temperature set to {temperature} (applies to Luna).")
                else:
                    print(f"{RESET + RED}Temperature {temperature}")
                continue
            elif request == "!multi":
                print(f"{RESET + GREEN}Multi-line input. Enter '!end' or hit Ctrl-D on a newline to finish:")
                contents = []
                while True:
                    try:
                        line = prompt('')
                        if line.strip() == '!end':
                            print(f"{RESET + GREEN}Finished multi-line input.")
                            break
                        contents.append(line)
                    except EOFError:
                        print(f"{RESET + GREEN}Finished multi-line input.")
                        break
                request = '\n'.join(contents)
            elif request == "!history":
                for msg in messages:
                    role = 'GPT' if msg['role'] == 'assistant' else msg['role']
                    color = GPTCOLOR if role == 'GPT' else USERCOLOR
                    print(f"{color}{role.upper()}: {msg['content']}\n")
                continue
            content = chat_stream(request)
            messages.append({"role": "assistant", "content": content})
    except KeyboardInterrupt:
        save_chat(resume_chat)

if len(sys.argv) > 1:
    if sys.argv[1] == '-l':
        try:
            directory = storage_location
            files = sorted((file for file in os.listdir(directory) if os.path.isfile(os.path.join(directory, file))), key=lambda x: os.path.getmtime(os.path.join(directory, x)))
            for file in files:
                with open(os.path.join(directory, file), 'r') as f:
                    data = json.load(f)
                    assistant_replies = sum(1 for item in data if item["role"] == "assistant")
                chat_size = os.path.getsize(os.path.join(directory, file))
                size_str = f"{chat_size} bytes" if chat_size < 1024 else f"{chat_size / 1024:.1f} KB"
                print(f"{file} ({RESET + GREEN}{size_str} - {assistant_replies} replies{RESET})")
        except Exception as e:
            print(f"{RESET + RED}An error occurred: {e}")
            sys.exit(1)
    elif sys.argv[1] == '-c':
        try:
            messages[0]["content"] = roles[2]["prompt"]
            messages.append({"role": "user", "content": sys.argv[2]})
            response = completion(messages)
            command = response.choices[0].message.content or ''
            print(f"{RED + ITALIC + BOLD}{command}")
            confirmation = input(f"{RESET + USERCOLOR}Execute command? [y/n] {RESET}").strip().lower()
            if confirmation == 'y':
                subprocess.run(command, shell=True)
            else:
                sys.exit()
        except KeyboardInterrupt:
            sys.exit()
    elif sys.argv[1] == '-i':
        size_options = {"p": "1024x1536", "l": "1536x1024"}
        image_size = "1024x1024"
        image_quality = "medium"
        image_prompt = None
        for arg in sys.argv[2:]:
            if arg in size_options:
                image_size = size_options[arg]
            elif arg == "hd":
                image_quality = "high"
            else:
                image_prompt = arg
        if not image_prompt:
            sys.exit("Usage: gpterm -i [p|l] [hd] 'image prompt'")
        response = get_client().images.generate(model=image_model, prompt=image_prompt, size=image_size, quality=image_quality, output_format="png")
        if not response.data or not response.data[0].b64_json:
            sys.exit("The API returned no image data.")
        image_bytes = base64.b64decode(response.data[0].b64_json)
        images_directory = storage_location / 'images'
        images_directory.mkdir(parents=True, exist_ok=True)
        current_time = datetime.datetime.now()
        filepath = images_directory / f"GPT-Image-{current_time.strftime('%H-%M-%S_%d-%m-%y')}.png"
        with open(filepath, 'wb') as file:
            file.write(image_bytes)
        print(f"file://{filepath}")
    elif sys.argv[1] == '-r':
        resume_chat = storage_location / sys.argv[2]
        with open(resume_chat, 'r') as f:
            messages = json.load(f)
            chat_loop(resume_chat)
    elif sys.argv[1] == '-h':
        print(f"""
    GPTerm: A Command-Line Interface for ChatGPT. Version 0.4

    USAGE:
        gpt [OPTION]... [QUESTION]

    OPTIONS:
        -l                  Lists all previous stored chats in {storage_location}.
        -r CHAT_NAME        Resumes a previous chat session. CHAT_NAME should be replaced with the name of the chat file.
        -c QUERY            Submits a QUERY to ChatGPT for a shell command and prompts the user to execute the command.
        -i PROMPT           Generates a PNG image with {image_model}, default 1024x1024.
                            Flags 'p' (1024x1536) or 'l' (1536x1024) select orientation.
                            Medium quality is used unless 'hd' (high quality) is used.
                            e.g. gpterm -i p hd 'a cat with a hat!'

    CHAT COMMANDS:
        !quit or !q         Ends the current chat and saves it with automatic naming.
        !kill               Ends the current chat without saving.
        !role               Cycle through roles
        !model              Cycle through Luna, Sol and Astra (default: Luna)
        !temperature        Set temperature: 0.0 to 2.0 (Luna only)
        !tokens             API token usage for the last reply (input, output and total)
        !history            Prints the current or resumed chat session history.
        !copy CODEBLOCK_ID  Copies the specified code block to the clipboard.
        !multi              Initiates multi-line input mode. Useful for pasting data with multiple lines such as code.
                            Finish multi-line entry with '!end' on a newline or hit CTRL-D.
    """)
    elif not sys.stdin.isatty():
        try:
            chat_stream(sys.argv[1] + ":\n\n" + sys.stdin.read())
        except:
            sys.exit()
    else:
        chat_stream(sys.argv[1])
else:
    chat_loop()
