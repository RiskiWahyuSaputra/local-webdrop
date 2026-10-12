#!/usr/bin/env fish
# Helper script to launch Local WebDrop in fish shell

set SCRIPT_DIR (status dirname)
cd $SCRIPT_DIR

set PORT 5050
set EXTRA_ARGS ""

for arg in $argv
    if test "$arg" = "--tunnel"
        set EXTRA_ARGS "$EXTRA_ARGS --tunnel"
    else if string match -qr '^[0-9]+$' $arg
        set PORT $arg
    end
end

echo "⚡ Menjalankan Local WebDrop pada port $PORT..."
python3 server.py $PORT $EXTRA_ARGS
