#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd ${DIR%%/}/../

if [ "$1" = "pypy" ]
then
        source ./dev_pypy/bin/activate
else
        source ./dev/bin/activate
fi

celery -A game_management.celery purge -f
