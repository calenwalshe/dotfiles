#!/bin/bash
# Dotfiles auto-sync - copies dotfiles to repo and commits if changed

DOTFILES_REPO="$HOME/Documents/projects/dotfiles"
LOG_FILE="$DOTFILES_REPO/.sync.log"

cd "$DOTFILES_REPO" || exit 1

# Copy current dotfiles to repo
cp ~/.zshrc zshrc 2>/dev/null
cp ~/.tmux.conf tmux.conf 2>/dev/null
cp ~/.od-manager.zsh od-manager.zsh 2>/dev/null
cp ~/.gitconfig gitconfig 2>/dev/null
cp ~/.vimrc vimrc 2>/dev/null

# Check if there are changes
if [[ -n $(git status --porcelain) ]]; then
    timestamp=$(date '+%Y-%m-%d %H:%M')
    git add -A
    git commit -m "Auto-sync: $timestamp"
    echo "[$timestamp] Committed changes" >> "$LOG_FILE"
fi
