#!/bin/bash

main() {
  git_pull

  if [ $? -eq 0 ]; then
    check_changes_and_deploy
    if [ $? -ne 0 ]; then
      echo "Error during deployment."
      exit 1
    fi
  else
    echo "Git pull failed. Exiting."
    exit 1
  fi

  echo "Deployment complete."
  exit 0
}

git_pull() {
  echo "Pulling the latest changes from Git..."
  GIT_PULL_OUTPUT=$(git pull origin main)
  if [ $? -ne 0 ]; then
      echo "Error: Failed to pull changes from Git."
      return 1
    fi
  return 0
}

check_changes_and_deploy() {
  CHANGED_FILES=$(echo "$GIT_PULL_OUTPUT" | awk '{if ($2 == "|") print $1}')

  if [ -z "$CHANGED_FILES" ]; then
    echo "No file changes detected."
    return 0
  fi

  echo "Changed files:"
  echo "$CHANGED_FILES"

  if echo "$CHANGED_FILES" | grep -q "compose.yaml"; then
    echo "compose.yaml has changed, restarting all"
    docker compose up -d --build
    if [ $? -ne 0 ]; then
        echo "Error: Failed to start some services."
        return 1
    fi
    # Return early as we've restarted everything
    return 0
  fi


  declare -a SERVICES_TO_RESTART=()

  if echo "$CHANGED_FILES" | grep -q "beats/filebeat/"; then
    echo "Changes detected in beats/filebeat/. Restarting filebeat..."
    SERVICES_TO_RESTART+=("filebeat")
  fi

  if echo "$CHANGED_FILES" | grep -q "beats/metricbeat/"; then
    echo "Changes detected in beats/metricbeat/. Restarting metricbeat..."
    SERVICES_TO_RESTART+=("metricbeat")
  fi

  if echo "$CHANGED_FILES" | grep -q "logstash/"; then
    echo "Changes detected in logstash/. Restarting logstash..."
    SERVICES_TO_RESTART+=("logstash")
  fi

  if echo "$CHANGED_FILES" | grep -q "kibana/"; then
      echo "Changes detected in kibana/. Restarting kibana..."
      SERVICES_TO_RESTART+=("kibana")
  fi

  if echo "$CHANGED_FILES" | grep -q "extensions/heartbeat"; then
        echo "Changes detected in extensions/heartbeat. Restarting heartbeat-monitor..."
        SERVICES_TO_RESTART+=("heartbeat-monitor")
  fi


  # Restart services
  if [ ${#SERVICES_TO_RESTART[@]} -gt 0 ]; then
      echo "Restarting the following services:"
      for SERVICE in "${SERVICES_TO_RESTART[@]}"; do
        echo "- $SERVICE"
      done

      docker compose pull "${SERVICES_TO_RESTART[@]}"
      docker compose up -d --build "${SERVICES_TO_RESTART[@]}"

      if [ $? -ne 0 ]; then
        echo "Error: Failed to start some services."
        return 1
      fi

    return 0
  fi

  echo "No services need to be restarted."
  return 0
}

main