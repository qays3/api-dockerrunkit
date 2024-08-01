#!/bin/bash


if [ $# -ne 1 ]; then
    echo "Usage: $0 <docker_run_command>"
    exit 1
fi


docker_run_command="$1"


log_file="docker_run.log"


log_message() {
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $1" >> "$log_file"
}


> "$log_file"


image_name=$(echo "$docker_run_command" | awk '{print $NF}')


container_name="container_$(date +%s%N | sha256sum | head -c10)"


docker_run_command_with_name=$(echo "$docker_run_command" | sed "s/docker run/docker run --name $container_name/")


eval "$docker_run_command_with_name >/dev/null 2>&1 &"
eval_status=$?

if [ $eval_status -ne 0 ]; then
    log_message "Failed to execute Docker run command: $docker_run_command_with_name"
    exit 1
fi

log_message "Docker container started with name: $container_name"


sleep 3600


docker stop $container_name >/dev/null 2>&1 &
docker rm $container_name >/dev/null 2>&1 &

log_message "Docker container $container_name has been stopped and removed."
