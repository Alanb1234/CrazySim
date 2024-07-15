# MARL UAV Coverage Problem

## Citation
[ICRA2024 paper](https://coogan.ece.gatech.edu/papers/pdf/llanes2024crazysim.pdf) as


```bibtex
@INPROCEEDINGS{LlanesICRA2024,
author = {Llanes, Christian and Kakish, Zahi and Williams, Kyle and Coogan, Samuel},
booktitle = {2024 IEEE International Conference on Robotics and Automation (ICRA)}, 
title = {CrazySim: A Software-in-the-Loop Simulator for the Crazyflie Nano Quadrotor},
year = {2024}
}
```

# Simulator Setup Steps

## Supported Platforms
This simulator works on Ubuntu systems with at least 20.04. This is primarily a requirement from Gazebo Sim. The simulator was built, tested, and verified on 22.04 with Gazebo Garden.

## 1). Clone the repo
To install this repository use the recursive command as shown below for HTTPS:
```bash
git clone https://github.com/Alanb1234/CrazySim.git --recursive
```

## 2). crazyflie-lib-python
```bash
cd ~/CrazySim/crazyflie-lib-python
pip install -e .
```

## 3). crazyflie-firmware
### Run the following commands to install dependencies.
```bash
sudo apt install cmake build-essential
pip install Jinja2
```

### First install Gazebo Garden from https://gazebosim.org/docs/garden/install_ubuntu

### Run the command to build the firmware and Gazebo plugins.

```bash
cd ~/CrazySim/crazyflie-firmware
mkdir -p sitl_make/build && cd $_
cmake ..
make all
```

## 4). Start up SITL manually (optional)

#### Spawning multiple crazyflie models with positions defined in the *agents.txt* file. New vehicles are defined by adding a new line with comma deliminated initial position *x,y*.
```bash
cd ~/CrazySim/crazyflie-firmware
bash tools/crazyflie-simulation/simulator_files/gazebo/launch/sitl_multiagent_text.sh -m crazyflie
```

Now you can run any CFLib Python script with URI `udp://0.0.0.0:19850`. For drone swarms increment the port for each additional drone.

## 5). Running the training simulation
```bash
cd ~/CrazySim/CoverageSim
python3 Training_Implementation.py
```





