#!/bin/bash


log_file="portidentification.log"


log_message() {
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $1" >> "$log_file"
}


if ! command -v docker &> /dev/null; then
    log_message "Error: Docker is not installed or not accessible."
    exit 1
fi


start_port=40000
end_port=59000


if [ "$start_port" -gt "$end_port" ]; then
    log_message "Error: Invalid port range. Start port must be less than or equal to end port."
    exit 1
fi

used_ports=$(docker ps --format '{{.Ports}}' | grep -oP '\d+(?=->)')


is_port_in_use() {
  local port=$1
  if echo "$used_ports" | grep -qw "$port"; then
    return 0   
  else
    return 1  
  fi
}


unused_port=""
for ((port=start_port; port<=end_port; port++)); do
  if ! is_port_in_use "$port"; then
    unused_port="$port"
    break
  fi
done

if [ -n "$unused_port" ]; then
  log_message "Unused port found: $unused_port"
  echo "$unused_port"
  exit 0
else
  log_message "No unused ports found in the range $start_port to $end_port"
  echo "No unused ports found in the range $start_port to $end_port"
  exit 1
fi
