# GPTerm

GPTerm is a tiny but full featured Python script that provides a command line interface for ChatGPT. It offers auto saved chat history, shell command generation, customisable roles, code block highlighting, multi-line input and many other simple usability features in a single script. 

![GPTerm](https://raw.githubusercontent.com/DeviousD4n/GPTerm/main/terminal.png)

## Suggested installation

Copy script to ~/.local/bin/gpterm and make executable. This will also allow chat list autocomplete (see below) to work correctly.

## Dependencies

Run the following command to install dependencies:

`pip install openai distro pyperclip prompt_toolkit`

## Usage

You can start a standard chat session by running the script with no arguments, or get single replies without entering a chat session by including your question:
```bash
gpterm "approximately how many emperor penguins can you fit in a lamborghini aventador?"
```
To enter multi-line data, such as code snippets, you can use the `!multi` command. Enter the lines of your input, and finish with `!end` on a new line.

Chat history will be automatically saved when you type `!quit`, or `!q`.

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

The following can be added for chat list autocmplete

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

Before using GPTerm, make sure to set your OpenAI API key by replacing the placeholder value `"API_KEY"` with your actual API key in the script. Extra roles and models can also be added in the script itself.
