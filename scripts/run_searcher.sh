if [ $(basename $(pwd)) == scripts ]; then
    cd ../
fi

source ./dev/bin/activate
celery -A game_management.celery worker --concurrency 1 -Q search -n worker.searcher -l=WARNING  # DO NOT CHANGE THE CONCURRENCY VALUE
