#!/bin/bash

SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

pkill -2 -f "hydraChess"
sudo service redis-server start

gnome-terminal -e "bash -c \"cd $SCRIPTS_DIR; ./purge_tasks.sh $1; ./run_high.sh $1\""
gnome-terminal -e "bash -c \"cd $SCRIPTS_DIR; ./run_normal.sh $1\""
gnome-terminal -e "bash -c \"cd $SCRIPTS_DIR; ./run_low.sh $1\""
gnome-terminal -e "bash -c \"cd $SCRIPTS_DIR; ./run_searcher.sh $1\""
gnome-terminal -e "bash -c \"cd $SCRIPTS_DIR; ./run_flower.sh $1\""
gnome-terminal -e "bash -c \"cd $SCRIPTS_DIR; ./run_app.sh $1\""
