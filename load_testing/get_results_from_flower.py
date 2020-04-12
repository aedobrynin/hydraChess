from requests import get


FLOWER_URL = "http://localhost:5555"


def show_make_move_stats():
    make_move_tasks = get(f"{FLOWER_URL}/api/tasks", data={"taskname": "make_move",
                                                           "limit": 1000000}).json()

    succeeded_lifetimes = list()
    total_tasks = len(make_move_tasks)
    succeeded_tasks = 0
    failed_tasks = 0


    for task in make_move_tasks.values():
        if task["state"] == 'SUCCESS':
            succeeded_tasks += 1

            lifetime = task["succeeded"] - task["received"]
            succeeded_lifetimes.append(lifetime)
        elif task["state"] == 'FAILED':
            failed_tasks += 1

    succeeded_lifetimes.sort()

    print("-- MAKE_MOVE STATS -- ")
    print(f"Total tasks: {total_tasks}")
    print(f"Succeded tasks: {succeeded_tasks} ({round(succeeded_tasks / total_tasks * 100, 3)}%)")
    print(f"Failed tasks: {failed_tasks} ({round(failed_tasks / total_tasks * 100, 3)}%)")
    print(f"Min lifetime: {succeeded_lifetimes[0]}. Max lifetime: {succeeded_lifetimes[-1]}")

    for val in (25, 50, 75, 90):
        print(f"{val}-th percentile: {succeeded_lifetimes[succeeded_tasks * val // 100]}")
    print("----------------------")


if __name__ == "__main__":
    show_make_move_stats()
