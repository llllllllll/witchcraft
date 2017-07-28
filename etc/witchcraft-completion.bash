function _witchcraft() {
    COMPREPLY=( $(witchcraft completions "${COMP_WORDS[@]:1}") )
}
complete -o default -F _witchcraft witchcraft
