#!/bin/bash
# launch_gazebo.sh

if [ "$1" == "start" ]; then
    echo "Starting Gazebo..."
    bash ~/CrazySim/crazyflie-firmware/tools/crazyflie-simulation/simulator_files/gazebo/launch/sitl_multiagent_text.sh -m crazyflie &
    echo $! > /tmp/gazebo_pid
    sleep 10

elif [ "$1" == "stop" ]; then
    echo "Stopping Gazebo..."
    if [ -f /tmp/gazebo_pid ]; then
        PID=$(cat /tmp/gazebo_pid)
        kill $PID
        rm /tmp/gazebo_pid
    else
        echo "No PID file found. Trying to find Gazebo process..."
        PIDS=$(pgrep -f "gzserver")
        if [ ! -z "$PIDS" ]; then
            echo "Found Gazebo process(es): $PIDS"
            kill $PIDS
        else
            echo "No Gazebo processes found."
        fi
    fi
    pkill -f gzclient
    sleep 2
else
    echo "Usage: launch_gazebo.sh {start|stop}"
fi



