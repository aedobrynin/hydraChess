#!/bin/bash

SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"


if [ "$1" = "pypy" ]
then
        source ${SCRIPTS_DIR}/../dev_pypy/bin/activate
else
        source ${SCRIPTS_DIR}/../dev/bin/activate
fi

python3 ${SCRIPTS_DIR}/../hydraChess/main.py
