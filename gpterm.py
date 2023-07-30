#!/usr/bin/env python3
import os
import sys
import datetime
import json
import openai
import subprocess

openai.api_key = "YOUR_API_KEY"
block_types = ["arduino","bash","c","cpp","csharp","css","diff","go","graphql","java","javascript","json","kotlin","latex","less","lua","makefile","makefile","markdown","matlab","mathematica","nginx","objectivec","perl","pgsql","php-template","php","plaintext","python-repl","python","r","ruby","rust","scss","shell","sql","swift","typescript","vbnet","wasm","xml","yaml"]
messages = [{"role": "system", "content": "You are a command line tool running on " + str(dict(line.strip().split('=') for line in open('/etc/os-release', 'r')).get('PRETTY_NAME', '')) + ". Succinct replies are better than long-winded explanations."}]
model = "gpt-3.5-turbo" #"gpt-3.5-turbo-16k"
code_blocks = {} 
block_id = 1

BOLD = "\033[1m"
ITALIC = "\033[3m"
RESET = "\033[0m"
GPTCOLOR = "\033[38;5;99m"
BLOCKCOLOR = "\033[38;5;200m"
USERCOLOR = "\033[38;5;75m"
COPYCOLOR = "\033[38;5;30m"
ERROR = "\033[38;5;1m"


def chat_stream(content):
    global block_id
    messages.append({"role": "user", "content": content})
    try:
        response = openai.ChatCompletion.create(model=model, messages=messages, stream=True)
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
                            print(f"\n{RESET + COPYCOLOR}╚═ codeblock {block_id} ═╝")
                            block_id += 1
                            code = '' 
                            language_found = False

                    elif len(buffer) > 3:
                        print(f"{ITALIC + BLOCKCOLOR if code_block else RESET + GPTCOLOR}{buffer[0]}", end='', flush=True)
                        buffer = buffer[1:]

        print(f"{BLOCKCOLOR if code_block else GPTCOLOR}{buffer}")
        return content 

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)


def save_chat(chat_history, chat_exists=None):
    if chat_exists is None:
        request = chat_history.copy()
        request.append({"role": "user", "content": "Thankyou. This chat has now concluded, can you please reply with a specific title for this entire conversation that uses a maximum of 4 words, shorter and more precise is better. No other text apart from these words should be included, as your reply will be directly saved as the title of the chat. As this will be a filename, spaces should be replaced with underscores and there can be no illegal characters. Only letters, numbers and underscores are allowed."})
        response = openai.ChatCompletion.create(model=model, messages=request)
        filename = response.choices[0]['message']['content'][:50]
        dirpath = os.path.expanduser(f"~/.local/share/gpterm/")
        os.makedirs(dirpath, exist_ok=True)  
        current_time = datetime.datetime.now()
        filepath = os.path.join(dirpath, filename) + "-" + current_time.strftime("%H-%M_%d-%m-%y")

    else:
        filepath = chat_exists

    with open(filepath, 'w') as f:
        f.write(json.dumps(chat_history))


def chat_loop(resume_chat=None):
    try:
        while True:
            request = input(f"\n{BOLD + USERCOLOR}ASK: ")
            if request in ('!quit', '!q'):
                save_chat(messages, resume_chat)
                break
            
            elif request == "!kill":
                break

            elif request.startswith('!copy '):
                copy_text = code_blocks.get(request.split(' ')[1], None)
                if copy_text:
                    subprocess.run('xclip -selection clipboard', input=copy_text, universal_newlines=True, check=True, shell=True)
                    print(f"{RESET + COPYCOLOR}Copied to clipboard")
                else:
                    print(f"{RESET + ERROR}Invalid input")
                continue

            elif request == "!multi":
                print("Multi-line input. Enter '!end' on a newline to finish:")  
                contents = []
                while True:
                    line = input()
                    if line == "!end":
                        break
                    contents.append(line)
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
            directory = os.path.expanduser("~/.local/share/gpterm")
            files = sorted((file for file in os.listdir(directory)), key=lambda x: os.path.getmtime(os.path.join(directory, x)))
            for file in files:
                print(file)
        except Exception as e:
            print(f"An error occurred: {e}")
            sys.exit(1)

    elif sys.argv[1] == '-r': 
        resume_chat = os.path.expanduser(f"~/.local/share/gpterm/{sys.argv[2]}")
        with open(resume_chat, 'r') as f:
            messages = json.load(f)
            chat_loop(resume_chat)

    elif sys.argv[1] == '-h': 
        print("""
    GPTerm: A Command-Line Interface for ChatGPT. Version 0.1
    
    USAGE:
        gpt [OPTION]... [QUESTION]

    DESCRIPTION:
        GPTerm interacts with ChatGPT in a terminal-based environment.

    OPTIONS:
        -l                  Lists all previous chats stored in ~/.local/share/gpterm.
        -r CHAT_NAME        Resumes a previous chat session. CHAT_NAME should be replaced with the name of the chat file.
        -h                  Displays this help message and exits.
              
    CHAT COMMANDS:
        !quit or !q         Ends the current chat and saves it.
        !kill               Ends the current chat without saving.
        !copy CODEBLOCK_ID  Copies the specified code block to the clipboard. Replace CODEBLOCK_ID with the ID of the code block.
        !history            Prints the current or resumed chat session history.
        !multi              Initiates multi-line input mode. Useful for pasting data with multiple lines such as code. 
                            Finish multi-line entry with '!end' on a newline.

    EXAMPLES:
        gpt
        gpt "Convert 100 meters to feet"
        gpt -l
        gpt -r example_chat.json
        gpt -h
    """)
    else:
        chat_stream(sys.argv[1])

else:
    chat_loop()
