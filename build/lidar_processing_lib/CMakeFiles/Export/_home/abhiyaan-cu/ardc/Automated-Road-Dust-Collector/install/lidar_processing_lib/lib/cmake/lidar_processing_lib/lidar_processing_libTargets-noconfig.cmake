#----------------------------------------------------------------
# Generated CMake target import file.
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "lidar_processing_lib" for configuration ""
set_property(TARGET lidar_processing_lib APPEND PROPERTY IMPORTED_CONFIGURATIONS NOCONFIG)
set_target_properties(lidar_processing_lib PROPERTIES
  IMPORTED_LOCATION_NOCONFIG "/home/abhiyaan-cu/ardc/Automated-Road-Dust-Collector/install/lidar_processing_lib/lib/liblidar_processing_lib.so"
  IMPORTED_SONAME_NOCONFIG "liblidar_processing_lib.so"
  )

list(APPEND _IMPORT_CHECK_TARGETS lidar_processing_lib )
list(APPEND _IMPORT_CHECK_FILES_FOR_lidar_processing_lib "/home/abhiyaan-cu/ardc/Automated-Road-Dust-Collector/install/lidar_processing_lib/lib/liblidar_processing_lib.so" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
