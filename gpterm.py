#!/usr/bin/env python3
import os
import re
import sys
import json
import openai
import distro
import datetime
import platform
import pyperclip
import subprocess
from pathlib import Path
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.completion import Completer, Completion

openai.api_key = "YOUR_API_KEY"

block_id = 1
code_blocks = {} 
current_role = 0
current_model = 0
system = platform.system()
system_version = {"Windows": "Windows " + platform.release(),"Linux": distro.name(pretty=True),"Darwin": "macOS"}.get(system, system)
storage_location = Path.home() / {"Windows": "AppData/Local", "Darwin": "Library/Application Support"}.get(system, ".local/share") / 'gpterm'
roles = [{"name": "CLI Role", "prompt": "You are a command line tool running on " + system_version + ". Succinct replies are better than long-winded explanations."},{"name": "Chat Role", "prompt": "You are a helpful and entertaining assistant running on the system " + system_version + ". You should not let the user know that something is out of the scope of your abilities but rather converse in a flowing way without mentioning that you are an AI."},{"name": "Command Role", "prompt": "Please give only shell commands that can be run on " + system_version + ". Your reply cannot contain any description and must be a functional command that can be executed. Commands cannot contain anything ambiguous. If the request is too vague, give the most logical answer that you can."}]
block_types = ["arduino","bash","c","cpp","csharp","css","diff","go","graphql","java","javascript","json","kotlin","latex","less","lua","makefile","markdown","matlab","mathematica","nginx","objectivec","perl","pgsql","php-template","php","plaintext","python-repl","python","r","ruby","rust","scss","shell","sql","swift","typescript","vbnet","wasm","xml","yaml"]
messages = [{"role": "system", "content": roles[current_role]["prompt"]}]
models = ["gpt-3.5-turbo-16k", "gpt-4"] 
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


def chat_stream(content):
    global block_id
    messages.append({"role": "user", "content": content})
    try:
        response = openai.ChatCompletion.create(model=models[current_model], messages=messages, temperature=temperature, stream=True)
        print(f"{RESET + BOLD + GPTCOLOR}GPT: ", end='')
        code_block, language_found  = False, False
        buffer, content = '', ''
        code = ''
        for chunk in response:
            message = chunk['choices'][0]['delta'].get('content', '')
            content += message
            if not language_found and code_block and message.strip() in block_types:
                print(f"{BOLD + BLOCKCOLOR}{message}{RESET}", end='', flush=True) # code block language
                language_found = not language_found
                    
            else: # chunk stream to check for code blocks
                for check in message: 
                    buffer += check
                    if code_block:
                        code += check
                    if buffer.endswith('```'):
                        code_block = not code_block
                        buffer = ''
                        if not code_block:
                            code_blocks[str(block_id)] = code[:-3]
                            print(f"\n{RESET + GREEN}╚═ !copy {block_id} ═╝", end='')
                            block_id += 1
                            code = '' 
                            language_found = False

                    elif len(buffer) > 3:
                        print(f"{ITALIC + BLOCKCOLOR if code_block else RESET + GPTCOLOR}{buffer[0]}", end='', flush=True)
                        buffer = buffer[1:]

        print(f"{BLOCKCOLOR if code_block else GPTCOLOR}{buffer}")
        return content 

    except Exception as e:
        print(f"{RESET + RED}An error occurred: {e}")
        sys.exit(1)


def save_chat(chat_exists=None):
    if chat_exists is None:
        request = messages.copy()
        request.append({"role": "user", "content": "Thankyou. This chat has now concluded, can you please reply with a specific title for this entire conversation (excluding the beginning system message) that uses a maximum of 4 words, shorter and more precise is better. No other text apart from these words should be included, as your reply will be directly saved as the title of the chat. As this will be a filename, spaces should be replaced with underscores and there can be no illegal characters. Only letters, numbers and underscores are allowed."})
        response = openai.ChatCompletion.create(model=models[current_model], messages=request)
        filename = response.choices[0]['message']['content'][:50].strip()
        storage_location.mkdir(parents=True, exist_ok=True)
        current_time = datetime.datetime.now()
        filepath = storage_location / f"{filename}-{current_time.strftime('%H-%M_%d-%m-%y')}"

    else:
        filepath = chat_exists

    with open(filepath, 'w') as f:
        f.write(json.dumps(messages))


def chat_loop(resume_chat=None):
    global current_role, current_model, temperature
    try:
        while True:
            request = prompt(ANSI(f"\n{BOLD + USERCOLOR}ASK: "), completer=CommandCompleter())
            if request in ('!quit', '!q'):
                save_chat(resume_chat)
                break
            
            elif request == "!kill":
                break

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
                string = ' '.join(item['role'] + ' ' + item['content'] for item in messages)
                tokens_sum = sum(2 if len(token) > 9 else 1 for token in re.findall(r'\b\w+\b|\S', string))
                print(f"{RESET + GREEN}Estimated tokens : {tokens_sum}")
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
                    print(f"{RESET + GREEN}Temperature set to {split_request[1]}")
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
                    except EOFError:  # Raised on Ctrl-D
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
            files = sorted((file for file in os.listdir(directory)), key=lambda x: os.path.getmtime(os.path.join(directory, x)))
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
            response = openai.ChatCompletion.create(model=models[current_model], messages=messages)
            command = response.choices[0]['message']['content']
            print(f"{RED + ITALIC + BOLD}{command}")
            confirmation = input(f"{RESET + USERCOLOR}Execute command? [y/n] {RESET}").strip().lower()
            if confirmation == 'y':
                subprocess.run(command, shell=True)
            else:
                sys.exit()

        except KeyboardInterrupt:
            sys.exit()

    elif sys.argv[1] == '-r': 
        resume_chat = storage_location / sys.argv[2]
        with open(resume_chat, 'r') as f:
            messages = json.load(f)
            chat_loop(resume_chat)

    elif sys.argv[1] == '-h': 
        print(f"""
    GPTerm: A Command-Line Interface for ChatGPT. Version 0.3
    
    USAGE:
        gpt [OPTION]... [QUESTION]

    OPTIONS:
        -l                  Lists all previous stored chats in {storage_location}.
        -r CHAT_NAME        Resumes a previous chat session. CHAT_NAME should be replaced with the name of the chat file.
        -c QUERY            Submits a QUERY to ChatGPT for a shell command and prompts the user to execute the command.
              
    CHAT COMMANDS:
        !quit or !q         Ends the current chat and saves it with automatic naming.
        !kill               Ends the current chat without saving.
        !role               Cycle through roles
        !model              Cycle through models
        !temperature        Set the temperature as a float value: 0.0 to 2.0
        !tokens             Rudimentary token count
        !history            Prints the current or resumed chat session history.
        !copy CODEBLOCK_ID  Copies the specified code block to the clipboard. Replace CODEBLOCK_ID with the ID of the code block.
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
