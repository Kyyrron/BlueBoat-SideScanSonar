from glob import glob

from setuptools import find_packages, setup

package_name = "blueboat_sss_sim"

setup(
    name=package_name,
    version="1.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages",
         ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
        ("share/" + package_name + "/launch", glob("launch/*.py")),
        ("share/" + package_name + "/docs", glob("docs/*.md")),
        ("share/" + package_name + "/msg_reference", glob("msg_reference/*.msg")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="BlueBoat SSS Team",
    maintainer_email="user@todo.todo",
    description="Synthetic Side Scan Sonar platform for the BlueBoat simulator",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            # ROS nodes
            "sss_sim_node = blueboat_sss.ros.sss_sim_node:main",
            "dataset_recorder_node = blueboat_sss.ros.dataset_recorder_node:main",
            "sss_path_generation = blueboat_sss.ros.sss_path_generation:main",
            "mavros_shim_node = blueboat_sss.ros.mavros_shim_node:main",
            # Offline tools
            "generate_world = blueboat_sss.worldgen.generate:main",
            "generate_mission = blueboat_sss.mission.generate:main",
        ],
    },
)
