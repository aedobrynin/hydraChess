if [ $(basename $(pwd)) == hydraChess ]; then
    cd scripts
fi

pkill -2 -f "hydraChess"
sudo service rabbitmq-server start

tmux_command="tmux new -c $(pwd) \
\"./purge_tasks.sh; ./run_high.sh\" ';' \
split \"./run_flower.sh\" ';' \
select-pane -t 0 ';' \
split -h \"./run_normal.sh\" ';' \
split -h \"./run_low.sh\" ';' \
select-pane -t {bottom} ';' \
split -h \"./run_app.sh\" ';' \
resize-pane -t 0 -L 15 ';' \
resize-pane -t 1 -L 7"

gnome-terminal -e "$tmux_command"
