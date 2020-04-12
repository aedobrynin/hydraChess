if [ $(basename $(pwd)) == hydraChess ]; then
    cd scripts
fi

pkill -2 -f "hydraChess"
sudo service redis-server start

gnome-terminal -e "bash -c \"./purge_tasks.sh; ./run_high.sh\""
gnome-terminal -e "bash -c \"./run_normal.sh\""
gnome-terminal -e "bash -c \"./run_low.sh\""
gnome-terminal -e "bash -c \"./run_searcher.sh\""
gnome-terminal -e "bash -c \"./run_flower.sh\""
gnome-terminal -e "bash -c \"./run_app.sh\""
