#!/usr/bin/env python3
import os
import sys
import datetime
import json
import openai

openai.api_key = "YOUR_API_KEY"
messages = [{"role": "system", "content": "You are a command line tool running on " + str(dict(line.strip().split('=') for line in open('/etc/os-release', 'r')).get('PRETTY_NAME', '')) + ". Succinct replies are better than long-winded explanations."}]
model = "gpt-3.5-turbo" #"gpt-3.5-turbo-16k"

BOLD = "\033[1m"
ITALIC = "\033[3m"
RESET = "\033[0m"
GPTCOLOR = "\033[38;5;99m"
BLOCKCOLOR = "\033[38;5;200m"
USERCOLOR = "\033[38;5;75m"


def chat_stream(content):
    messages.append({"role": "user", "content": content})
    try:
        response = openai.ChatCompletion.create(model=model, messages=messages, stream=True)
        print(f"{RESET + GPTCOLOR}GPT: ", end='')
        code_block = False
        buffer, content = '', ''
        for chunk in response:
            message = chunk['choices'][0]['delta'].get('content', '')
            content += message
            for check in message:
                buffer += check
                if buffer.endswith('```'):
                    code_block = not code_block
                    buffer = ''
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
    while True:
        request = input(f"\n{BOLD + USERCOLOR}ASK: ")
        if request in ('!quit', '!exit', '!q'):
            save_chat(messages, resume_chat)
            break

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
        print("""GPTerm for ChatGPT in the terminal. Version 0.1
  Use without flags for a standard chat: 'gpt', chats are saved on 'quit' or 'exit'. Entering 'multi' allows for pasting of multiple line data such as code. Finish multi-line entry with 'END' on a newline.
  Use with question in quotes for single reply: 'gpt "Convert 100 meters to feet"'.
    -l  List all previous chats (stored in ~/.local/share/gpterm)
    -r CHATNAME Resume a previous chat""")
    else:
        chat_stream(sys.argv[1])

else:
    chat_loop()