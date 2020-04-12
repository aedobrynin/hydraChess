if [ $(basename $(pwd)) == hydraChess ]; then
    cd scripts
fi

pkill -2 -f "hydraChess"
sudo service redis-server start

tmux_command="tmux new -c $(pwd) \
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
