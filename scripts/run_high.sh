#!/bin/bash

SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${SCRIPTS_DIR}/../dev/bin/activate
cd ${SCRIPTS_DIR}/..
celery -A hydraChess.game_management.celery worker --concurrency 30 -Q high -n worker.high -l=WARNING
