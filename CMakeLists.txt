cmake_minimum_required(VERSION 2.8.3)
project(agimus_demos)

## Compile as C++11, supported in ROS Kinetic and newer
# add_compile_options(-std=c++11)

## Find catkin macros and libraries
## if COMPONENTS list like find_package(catkin REQUIRED COMPONENTS xyz)
## is used, also find other catkin packages
find_package(catkin REQUIRED COMPONENTS
  roslaunch
  robot_state_publisher
)

catkin_package(
#  INCLUDE_DIRS include
#  LIBRARIES agimus_demos
#  CATKIN_DEPENDS roslaunch
#  DEPENDS system_lib
)
find_package(Eigen3)

MACRO(INSTALL_DEMO_LAUNCH_FILES DEMO)
  set(options)
  set(oneValueArgs)
  set(multiValueArgs LAUNCHFILES SCRIPTS)
  cmake_parse_arguments(ARG "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})
  FILE(RELATIVE_PATH robot ${CMAKE_SOURCE_DIR} ${CMAKE_CURRENT_SOURCE_DIR})
  MESSAGE(STATUS "Add demonstration ${robot}/${DEMO}")
  FOREACH (launch_file ${ARG_LAUNCHFILES})
    install(FILES
      ${DEMO}/${launch_file}
      DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/launch
      RENAME ${robot}_${DEMO}_${launch_file}
    )
  ENDFOREACH ()
  FOREACH (script_file ${ARG_SCRIPTS})
    install(PROGRAMS "${DEMO}/${script_file}"
      DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
      RENAME ${robot}_${DEMO}_${script_file})
  ENDFOREACH ()
ENDMACRO()

ADD_SUBDIRECTORY(talos)
ADD_SUBDIRECTORY(tiago)
add_subdirectory(src)
add_subdirectory(tests)

# Install talos/calibration/apriltags launch files
INSTALL(FILES
  talos/calibration/apriltags/demo.launch
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/launch
  RENAME talos_calibration_apriltags.launch
  )
INSTALL(FILES talos/calibration/apriltags/tracker.launch
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/launch
  RENAME talos_calibration_apriltags_tracker.launch
  )
INSTALL(FILES talos/calibration/apriltags/on_pyrene.launch
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/launch
  RENAME talos_calibration_apriltags_on_pyrene.launch
  )

# Install other files with the same hierarchy as here.
install(DIRECTORY talos tiago urdf srdf meshes
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
  FILES_MATCHING
  PATTERN "*"
  PATTERN "*.launch" EXCLUDE
)

install(PROGRAMS
  scripts/gazebo_object_to_tf.py
  scripts/visual_tag_initializer.py
  scripts/calibration_frames_grabber.py
  scripts/publish_constants.py
  scripts/group_of_tags.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})
