#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

pkill -2 -f "hydraChess"
sudo service redis-server start

tmux_command="tmux new -c $DIR \
\"./purge_tasks.sh $1; ./run_high.sh $1\" ';' \
split \"./run_flower.sh $1\" ';' \
select-pane -t 0 ';' \
split -h \"./run_normal.sh $1\" ';' \
select-pane -t 2 ';' \
split -h \"./run_low.sh $1\" ';' \
split -h \"./run_searcher.sh $1\" ';' \
select-pane -t {bottom} ';' \
split -h \"./run_app.sh $1\" ';'"

gnome-terminal -e "$tmux_command"
