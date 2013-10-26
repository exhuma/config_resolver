#!/bin/bash

#
# Simple script to launch a vim session with two nosetest sniffers
#

tmux new -d "vim config_resolver.py"
tmux split-window -h './env/bin/sniffer -x --with-coverage -x --cover-package=config_resolver'
tmux split-window './env3/bin/sniffer -x --with-coverage -x --cover-package=config_resolver'
tmux select-pane -t 0
tmux attach
