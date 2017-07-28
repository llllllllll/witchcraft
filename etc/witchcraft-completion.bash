function _witchcraft() {
    COMPREPLY=( $(witchcraft completions "${COMP_WORDS[@]:1}") )
    [[ $COMPREPLY ]] && return

    compopt -o bashdefault -o default
    compgen
}
complete -o nospace -F _witchcraft witchcraft
