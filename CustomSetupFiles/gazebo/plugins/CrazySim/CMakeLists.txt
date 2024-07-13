cmake_minimum_required(VERSION 3.11.0 FATAL_ERROR)

# find_package(gz-cmake3 REQUIRED)

project(crazysim_gz VERSION 1.1.0)

find_package(gz-plugin REQUIRED COMPONENTS register NAMES gz-plugin2)
set(GZ_PLUGIN_VER ${gz-plugin_VERSION_MAJOR})

set(GZ_SIM_FOUND FALSE)
foreach(ver 8 7) # replace with future gz-sim versions
  if(NOT GZ_SIM_FOUND)
    find_package(gz-sim NAMES gz-sim${ver})
    if(gz-sim_FOUND)
      set(GZ_SIM_VER ${gz-sim_VERSION_MAJOR})
      set(GZ_SIM_FOUND TRUE)
    endif()
  endif()
endforeach()

if(NOT GZ_SIM_FOUND)
  message(FATAL_ERROR "gz-sim not found")
endif()

if(GZ_SIM_VER EQUAL 8)
  message("Found Gazebo 8: Harmonic")
  find_package(gz-transport REQUIRED NAMES gz-transport13)
  find_package(gz-msgs REQUIRED NAMES gz-msgs10)
elseif(GZ_SIM_VER EQUAL 7)
  message("Found Gazebo 7: Garden")
  find_package(gz-transport REQUIRED NAMES gz-transport12)
  find_package(gz-msgs REQUIRED NAMES gz-msgs9)
endif()

set(GZ_TRANSPORT_VER ${gz-transport_VERSION_MAJOR})
set(GZ_MSGS_VER ${gz-msgs_VERSION_MAJOR})

find_package(PkgConfig REQUIRED)

#======================================= CrazySim PLUGIN ==========================================//
add_library(gz_crazysim_plugin SHARED crazysim_plugin.cpp)
set_property(TARGET gz_crazysim_plugin PROPERTY CXX_STANDARD 17)
target_link_libraries(gz_crazysim_plugin 
  PRIVATE
    gz-plugin${GZ_PLUGIN_VER}::gz-plugin${GZ_PLUGIN_VER}
    gz-sim${GZ_SIM_VER}::gz-sim${GZ_SIM_VER}
    gz-msgs${GZ_MSGS_VER}::gz-msgs${GZ_MSGS_VER}
    gz-transport${GZ_TRANSPORT_VER}::core
)
#==============================================================================================//

include(GNUInstallDirs)
install(TARGETS
  gz_crazysim_plugin
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
)