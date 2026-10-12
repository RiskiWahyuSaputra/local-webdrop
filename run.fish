#!/usr/bin/env fish
# Helper script to launch Local WebDrop in fish shell

set SCRIPT_DIR (status dirname)
cd $SCRIPT_DIR

set PORT 5050
if test (count $argv) -ge 1
    set PORT $argv[1]
end

echo "⚡ Menjalankan Local WebDrop pada port $PORT..."
python3 server.py $PORT
