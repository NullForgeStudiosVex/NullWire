#!/bin/bash

BASE_DIR="$(dirname "$(realpath "$0")")"
cd "$BASE_DIR" || exit


if pgrep -fx "$(realpath "$0")" | grep -v $$ > /dev/null; then
    echo "Watchdog already running. Exiting."
    exit 0
fi

PYTHON="$BASE_DIR/venv/bin/python3"
SCRIPT="$BASE_DIR/NullWire.py"

while true; do
if ! pgrep -x "NullWire" > /dev/null; then
echo "Starting NullWire..."
nohup "$PYTHON" "$SCRIPT" > /dev/null 2>&1 &
#"$PYTHON" "$SCRIPT"
disown
fi

```
sleep 5
```

done
