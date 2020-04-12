if [ $(basename $(pwd)) == scripts ]; then
    cd ../
fi

source ./dev/bin/activate
celery -A game_management.celery worker --concurrency 20 -Q high -n worker.high -l=INFO
