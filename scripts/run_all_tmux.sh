#!/bin/bash

SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

pkill -2 -f "hydraChess"
sudo service redis-server start

tmux_command="tmux new -c $SCRIPTS_DIR \
\"./purge_tasks.sh; ./run_high.sh\" ';' \
split \"./run_flower.sh\" ';' \
select-pane -t 0 ';' \
split -h \"./run_normal.sh\" ';' \
select-pane -t 2 ';' \
split -h \"./run_low.sh\" ';' \
split -h \"./run_searcher.sh\" ';' \
select-pane -t {bottom} ';' \
split -h \"./run_app.sh\" ';'"

gnome-terminal -e "$tmux_command"
