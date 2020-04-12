if [ $(basename $(pwd)) == scripts ]; then
    cd ../
fi

source ./dev/bin/activate
celery -A game_management.celery worker --concurrency 25 -Q normal -n worker.normal -l=INFO
