#! /bin/bash

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
cd $SCRIPT_DIR/..

# check updates every 30 mins
TIME=$((60*1))
echo "start run"
python . &
my_pid=$!
while true
do
	sleep $TIME
	echo "start update"
	git pull --force
	echo "start test"
	make test
	if [ $? -eq 0 ];
	then
		echo test ok
		echo "relaunch"
		kill $my_pid
		python . &
	else
		echo test fails
	fi
done
