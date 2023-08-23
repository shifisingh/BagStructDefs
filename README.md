# BagStructDefs

## Permissions
generate_bagstructdefs.py is a script which aids in vehicle post dive processing within the National Deep Submergence Facility.
It has been reproduced for a personal repository with permission from Woods Hole Oceanographic Institution.

## Rationale 
NDSF is home to three underwater vehicles: Jason, Alvin, and Sentry. This script was written as part of a larger effort 
within the facility to move towards unification of vehicle post dive processing for three vehicles into one single pipeline. 

## Overview 
This script, when run as part of the larger NDSF post dive processing ecosystem, produces the necessary structures to enable
plotting of crucial dive data. These structures are the rosbag definitions ('bag defs') and matlab structs ('struct defs')
in the form of .yaml configuration files. 

Depending on the level of granularity specified by the user on the command line, the script pulls an intelligent
selection of ROS data, pipes the output of running necessary ROS commands on this data into .txt files, and then 
parses information from those files, setting off a cascade of object instantiation and manipulation. Relevant information 
is also parsed from standard ROS .msg definitions and custom NDSF ROS .msg definitions. 

## Notes
There are a few interesting complexities to the data. Many .msg definition contain nested .msg definitions, meaning 
a recursive traversal of .msg paths was implemented (see the structFieldsUnwrapped field of a BagStructDefs object). 

There exists terabytes of ROS data on the NDSF servers. To keep the script fast, there are two main strategies: Firstly,
the _mode_ command line argument introduces a tradeoff -- there is greater granularity in ROS data selected for 
smaller amounts of data being analyzed. Secondly, selected ROS data on which commands must be run use _rsync_ -- so 
the commands get run on local files over server files, reducing the load on the server as well as the time it takes 
for the structs to populate.

Automation for struct defs is less straightforward than automation for bag defs because there exist inconsistencies
between .msg def files and what should get populated to the .yaml configuration files. Said differently, there does not
exist an exact one-to-one ratio of .msg definitions to .yaml config files. A more interactive process was thus designed, 
handling known custom types automatically, and flagging potentially custom types and asking the user
for input on these flagged types. 

The resulting populate_struct method has grown more complex than was originally anticipated
and the next version will introduce a new object for all the populate subprocesses to reside in.

Similarly, a new object will be created which houses the necessary paths to .msg files, as a cleaner and less 
machine specific alternative to the current hardcoded paths. 

