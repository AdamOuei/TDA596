#!/usr/bin/env bash
set -e
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null && pwd)"
IP=10.1.0.3
for i in $(seq 1 20); do
  curl -d 'entry=t'$i -X 'POST' "http://${IP}:80/board" &
done
