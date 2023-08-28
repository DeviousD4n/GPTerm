#!/usr/bin/env python3
import os
import re
import sys
import json
import openai
import datetime
import platform
import distro
import pyperclip
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
roles = [{"name": "CLI Role", "prompt": "You are a command line tool running on " + system_version + ". Succinct replies are better than long-winded explanations."},{"name": "Chat Role", "prompt": "You are a helpful and entertaining assistant running on the system " + system_version + ". You should not let the user know that something is out of the scope of your abilities but rather converse in a flowing way without mentioning that you are an AI."}]
block_types = ["arduino","bash","c","cpp","csharp","css","diff","go","graphql","java","javascript","json","kotlin","latex","less","lua","makefile","markdown","matlab","mathematica","nginx","objectivec","perl","pgsql","php-template","php","plaintext","python-repl","python","r","ruby","rust","scss","shell","sql","swift","typescript","vbnet","wasm","xml","yaml"]
messages = [{"role": "system", "content": roles[current_role]["prompt"]}]
models = ["gpt-3.5-turbo-16k", "gpt-4", "gpt-3.5-turbo"] 

BOLD = "\033[1m"
ITALIC = "\033[3m"
RESET = "\033[0m"
GPTCOLOR = "\033[38;5;99m"
BLOCKCOLOR = "\033[38;5;200m"
USERCOLOR = "\033[38;5;75m"
GREEN = "\033[38;5;30m"
ERROR = "\033[38;5;1m"


class CommandCompleter(Completer):
    def get_completions(self, document, complete_event):
        if document.text.startswith('!'):
            for command in ['!quit', '!kill', '!role', '!model', '!tokens', '!copy ', '!multi', '!history']:
                if command.startswith(document.text):
                    yield Completion(command, start_position=-len(document.text))


def chat_stream(content):
    global block_id
    messages.append({"role": "user", "content": content})
    try:
        response = openai.ChatCompletion.create(model=models[current_model], messages=messages, stream=True)
        print(f"{RESET + GPTCOLOR}GPT: ", end='')
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
                            print(f"\n{RESET + GREEN}╚═ !copy {block_id} ═╝")
                            block_id += 1
                            code = '' 
                            language_found = False

                    elif len(buffer) > 3:
                        print(f"{ITALIC + BLOCKCOLOR if code_block else RESET + GPTCOLOR}{buffer[0]}", end='', flush=True)
                        buffer = buffer[1:]

        print(f"{BLOCKCOLOR if code_block else GPTCOLOR}{buffer}")
        return content 

    except Exception as e:
        print(f"{RESET + ERROR}An error occurred: {e}")
        sys.exit(1)


def save_chat(chat_history, chat_exists=None):
    if chat_exists is None:
        request = chat_history.copy()
        request.append({"role": "user", "content": "Thankyou. This chat has now concluded, can you please reply with a specific title for this entire conversation that uses a maximum of 4 words, shorter and more precise is better. No other text apart from these words should be included, as your reply will be directly saved as the title of the chat. As this will be a filename, spaces should be replaced with underscores and there can be no illegal characters. Only letters, numbers and underscores are allowed."})
        response = openai.ChatCompletion.create(model=models[current_model], messages=request)
        filename = response.choices[0]['message']['content'][:50].strip()
        storage_location.mkdir(parents=True, exist_ok=True)
        current_time = datetime.datetime.now()
        filepath = storage_location / f"{filename}-{current_time.strftime('%H-%M_%d-%m-%y')}"

    else:
        filepath = chat_exists

    with open(filepath, 'w') as f:
        f.write(json.dumps(chat_history))


def chat_loop(resume_chat=None):
    global current_role, current_model
    try:
        while True:
            request = prompt(ANSI(f"\n{BOLD + USERCOLOR}ASK: "), completer=CommandCompleter())
            if request in ('!quit', '!q'):
                save_chat(messages, resume_chat)
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
                    print(f"{RESET + ERROR}Invalid input")
                continue

            elif request == "!multi":
                print(f"{RESET + GREEN}Multi-line input. Enter '!end' or hit Ctrl-D on a newline to finish:")
                contents = []
                while True:
                    try:
                        line = prompt('')
                        if line.strip() == '!end':
                            print(f"{RESET + GREEN}\nFinished multi-line input.")
                            break
                        contents.append(line)
                    except EOFError:  # Raised on Ctrl-D
                        print(f"{RESET + GREEN}\nFinished multi-line input.")
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
        save_chat(messages, resume_chat)


if len(sys.argv) > 1:
    if sys.argv[1] == '-l':
        try:
            directory = storage_location
            files = sorted((file for file in os.listdir(directory)), key=lambda x: os.path.getmtime(os.path.join(directory, x)))
            for file in files:
                print(file)
        except Exception as e:
            print(f"{RESET + ERROR}An error occurred: {e}")
            sys.exit(1)

    elif sys.argv[1] == '-r': 
        resume_chat = storage_location / sys.argv[2]
        with open(resume_chat, 'r') as f:
            messages = json.load(f)
            chat_loop(resume_chat)

    elif sys.argv[1] == '-h': 
        print("""
    GPTerm: A Command-Line Interface for ChatGPT. Version 0.2
    
    USAGE:
        gpt [OPTION]... [QUESTION]

    OPTIONS:
        -l                  Lists all previous stored chats in .
        -r CHAT_NAME        Resumes a previous chat session. CHAT_NAME should be replaced with the name of the chat file.
              
    CHAT COMMANDS:
        !quit or !q         Ends the current chat and saves it.
        !kill               Ends the current chat without saving.
        !role               Cycle through roles
        !model              Cycle through models
        !tokens             Rudimentary token count
        !history            Prints the current or resumed chat session history.
        !copy CODEBLOCK_ID  Copies the specified code block to the clipboard. Replace CODEBLOCK_ID with the ID of the code block.
        !multi              Initiates multi-line input mode. Useful for pasting data with multiple lines such as code. 
                            Finish multi-line entry with '!end' on a newline or hit CTRL-D.
    """)
    else:
        chat_stream(sys.argv[1])

else:
    chat_loop()
