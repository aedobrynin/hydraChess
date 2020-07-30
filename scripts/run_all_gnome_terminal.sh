#!/bin/bash

SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

pkill -2 -f "hydraChess"
sudo service redis-server start

gnome-terminal -e "bash -c \"cd $SCRIPTS_DIR; ./purge_tasks.sh; ./run_high.sh\""
gnome-terminal -e "bash -c \"cd $SCRIPTS_DIR; ./run_normal.sh\""
gnome-terminal -e "bash -c \"cd $SCRIPTS_DIR; ./run_low.sh\""
gnome-terminal -e "bash -c \"cd $SCRIPTS_DIR; ./run_searcher.sh\""
gnome-terminal -e "bash -c \"cd $SCRIPTS_DIR; ./run_flower.sh\""
gnome-terminal -e "bash -c \"cd $SCRIPTS_DIR; ./run_app.sh\""
