# GPTerm

GPTerm is a tiny but full featured Python script that provides a command line interface for ChatGPT. It offers auto saved chat history, shell command generation, piping, customisable roles, code block highlighting, multi-line input, image generation with Dall-E 3 and many other simple usability features in a single script. 

![terminal](https://github.com/DeviousD4n/GPTerm/assets/129655658/0b077a53-229b-40a8-8b85-763df1e542b0)

![terminal2](https://github.com/DeviousD4n/GPTerm/assets/129655658/2f3fde65-fc74-498b-a8ee-f2c3ad962ee7)


## Suggested installation

Copy script to ~/.local/bin/gpterm and make executable. This will also allow chat list autocomplete (see below) to work correctly.

## Dependencies

Run the following command to install dependencies:

`pip install openai distro pyperclip prompt_toolkit`

## Usage

You can start a standard chat session by running the script with no arguments, or get single replies without entering a chat session by including your question:
```bash
$ gpterm "approximately how many emperor penguins can you fit in a lamborghini aventador?"
```

```bash
$ uptime | gpterm "How's the system load looking?"
GPT: The system load average is 0.89, 0.84, and 0.81, indicating a moderate load on the system.
```

```bash
$ gpterm -c "can you search the current directory for files containing 'gpt-3.5'?"    
grep -r "gpt-3.5" .
Execute command? [y/n] y
./gptbackup.py:        response = openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=messages, stream=True)
./chatgpt-stream/gpterm.py:model = "gpt-3.5-turbo-16k" #"gpt-3.5-turbo-16k"
./gptterm-prompt:models = ["gpt-3.5-turbo-16k", "gpt-4"]
./gptbs4.py:        model='gpt-3.5-turbo',
```

To enter multi-line data, such as code snippets, you can use the `!multi` command. Enter the lines of your input, and finish with `!end` on a new line or with `CTRL-D` .

Chat history will be automatically saved when you type `!quit`, or `!q`.

### Generate images with Dall-E 3

```bash
$ gpterm -i "an emperor penguin in a lamborghini aventador"
```

Default size and quality are used unless flags 'p' (1024x1792) or 'l' (1792x1024) are specified, HD quality can be specified with the flag 'hd'. The openai library may need to be updated if you have an old version `pip install openai --upgrade`

```bash
$ gpterm -i l hd "an emperor penguin in a lamborghini aventador"
```
![img-9tcIdP8VGnzug5k5KLEytsnb](https://github.com/DeviousD4n/GPTerm/assets/129655658/3125eca2-8100-4e95-b224-5d26dbf230d4)

### Listing Previous Chats

You can list all previous chat sessions by using the `-l` flag:
```bash
gpterm -l
```
This will display the names of all the chat files in the default directory `~/.local/share/gpterm`.

### Resuming Previous Chats

You can resume a previous chat session by providing the `-r` flag followed by the name of the chat to resume:
```bash
gpterm -r CHAT_NAME
```
You can view previous chat history once resumed by typing `!history`. 

### Chat Resume Autocomplete

The following can be added for chat list autocomplete

Add to .bashrc
```bash
_gpterm_completion() {
  local curr_word
  local -a opts 
  curr_word="${COMP_WORDS[COMP_CWORD]}"
  while IFS= read -r line; do
    opts+=("$line")
  done < <(gpterm -l | awk -F '(' '{print $1}' | sed 's/ *$//')
  COMPREPLY=($(compgen -W "${opts[*]}" -- "$curr_word"))
  return 0
}
complete -F _gpterm_completion gpterm
```

Add to .zshrc
```zsh
function _gpt_completion {
  local -a opts
  IFS=$'\n' opts=($(gpterm -l | awk -F '(' '{print $1}' | sed 's/ *$//'))
  _describe 'values' opts
}
compdef _gpt_completion gpterm
```

## Configuration

Before using GPTerm, make sure to set your OpenAI API key by replacing the placeholder value `"YOUR_API_KEY"` with your actual API key in the script. Extra roles and models can also be added in the script itself.

## gpterm -h :

    GPTerm: A Command-Line Interface for ChatGPT. Version 0.2
    
    USAGE:
        gpt [OPTION]... [QUESTION]

    OPTIONS:
        -l                  Lists all previous stored chats in {storage_location}.
        -r CHAT_NAME        Resumes a previous chat session. CHAT_NAME should be replaced with the name of the chat file.
        -c QUERY            Submits a QUERY to ChatGPT for a shell command and prompts the user to execute the command.
        -i PROMPT           Generates an image with Dall-E 3, default size is used unless flags 'p' (1024x1792) or 'l' (1792x1024) are specified.
                            Standard quality is used unless the flag 'hd' is used. e.g. gpterm -i p hd 'a cat with a hat!'
              
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
