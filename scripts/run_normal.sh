#!/bin/bash

SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${SCRIPTS_DIR}/../dev/bin/activate
cd ${SCRIPTS_DIR}/..
celery -A hydraChess.game_management.celery worker --concurrency 25 -Q normal -n worker.normal -l=WARNING
