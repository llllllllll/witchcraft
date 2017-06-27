function _witchcraft() {
    COMPREPLY=( $(witchcraft completions "${COMP_WORDS[@]:1}") )
}
complete -o nospace -F _witchcraft witchcraft
