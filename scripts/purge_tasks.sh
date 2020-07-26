#!/bin/bash

SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [ "$1" = "pypy" ]
then
        source ${SCRIPTS_DIR}/../dev_pypy/bin/activate
else
        source ${SCRIPTS_DIR}/../dev/bin/activate
fi

cd ${SCRIPTS_DIR}/../hydraChess
celery -A game_management.celery purge -f
