if [ $(basename $(pwd)) == scripts ]; then
    cd ../
fi

source ./dev/bin/activate
celery -A game_management.celery worker --concurrency 30 -Q high -n worker.high -l=INFO
