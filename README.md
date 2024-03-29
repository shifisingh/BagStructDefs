# BagStructDefs

## Permissions
generate_bagstructdefs.py is a script which aids in vehicle post dive processing within the National Deep Submergence Facility.
It has been reproduced for a personal repository with permission from Woods Hole Oceanographic Institution. 

## Rationale 
NDSF is home to three underwater vehicles: Jason, Alvin, and Sentry. This script was written as part of a larger effort within the facility to move towards unification of vehicle post dive processing for three vehicles into one single pipeline.  

This script, when run as part of the larger NDSF post dive processing ecosystem, produces the necessary structures to enable plotting of crucial dive data. These structures are the rosbag definitions ('bag defs') and matlab structs ('struct defs') in the form of .yaml configuration files. Prior to the script, the post dive included manually updating configuration files across vehicles, namespaces, and topics. The script eliminates the need for this manual updating, as well as the inevitable errors and missing data which come along with such a manual process.  

## Overview 
Depending on the level of granularity specified by the user on the command line, the script pulls an intelligent selection of ROS data, pipes the output of running necessary ROS commands on this data into .txt files, and then parses information from those files, setting off a cascade of object instantiation and manipulation. Relevant information is also parsed from standard ROS .msg definitions and custom NDSF ROS .msg definitions. In keeping with the rationale, a single script is used for Jason, Alvin, and Sentry, with a command line argument to specify which vehicle the user wishes to create files for. 

## Notes 
There are a few interesting complexities to the data. Many .msg definitions contain nested .msg definitions, meaning a recursive traversal of .msg paths was implemented (see the structFieldsUnwrapped field of a BagStructDefs object). 

There exists terabytes of ROS data on the NDSF servers. To keep the script fast, there are two main strategies: Firstly, the mode command line argument introduces a tradeoff -- there is greater granularity in ROS data selected for smaller amounts of data being analyzed. Secondly, selected ROS data on which commands must be run use rsync -- so the commands get run on local files over server files, reducing the load on the server as well as the time it takes for the structs to populate. 

Automation for struct defs is less straightforward than automation for bag defs because there exist inconsistencies between .msg def files and what should get populated to the .yaml configuration files. Said differently, there does not exist an exact one-to-one ratio of .msg definitions to .yaml config files. A more interactive process was thus designed, building support to handle known custom types automatically, and asking for user input on types flagged as potentially custom. 

## Future Work 
The script is still in development. 

The populate_struct method has grown more complex than was originally anticipated and the next version will introduce a new object for all the populate subprocesses to reside in, effectively serving as a front-end configuration. 

A new object will be created which houses the necessary paths to .msg files, as a cleaner and less machine specific alternative to the current hardcoded paths. This also allows for easily maintainable support as new drivers/nodes are added, particularly in the world of Sentry.  

Currently, the code is housed in a singular file but split into different classes. This allows for ease in running the script from the Linux command line. Future work includes splitting each class into a seperate .py file and using a third party tool to compile the multiple .py files into one command line argument. 
