#!/bin/bash
# Install dotfiles on a new machine
# Usage: ./install.sh

set -e

DOTFILES_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing dotfiles from $DOTFILES_DIR..."

# Symlink each dotfile
for file in .zshrc .tmux.conf .gitconfig .vimrc .bashrc; do
    if [ -f "$DOTFILES_DIR/$file" ]; then
        if [ -f "$HOME/$file" ] && [ ! -L "$HOME/$file" ]; then
            echo "  Backing up existing $file to $file.backup"
            mv "$HOME/$file" "$HOME/$file.backup"
        fi
        ln -sf "$DOTFILES_DIR/$file" "$HOME/$file"
        echo "  ✓ Linked $file"
    fi
done

echo ""
echo "✓ Dotfiles installed!"
echo "  Restart your shell or run: source ~/.zshrc"
