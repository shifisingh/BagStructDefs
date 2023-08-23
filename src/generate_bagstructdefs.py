# author: Shefali Singh, shefali.singh@whoi.edu
# version: 1.0.0, 8/23

# only thing you should be doing manually is 
# updating the vehiclename_extract.yaml file with new namespaces. 

# cumulative is the .csv files and the .yaml files in /bag_defs and /struct_defs 
# the class objects run for a specific configuration. without a populate method
# called, /bag_defs and /struct_defs do not change. in other words,
# objects instantiation alone does not alter contents of /bag_defs and /struct_defs
# and functionality outside the purpose of bag/struct generation can be extracted
# by object manipulation
 

# to do for next version:

# the script as it is overrides manual changes to the files, may not be desired behavior

# certain topics end in vehicle name or primitive type i.e. sonardyne, create filter
# (probably in backend) method to handle such cases 

# develop cleaner ways of path traversal for .msg, workspace, dslpp (idea -- MsgPath() object
# which instantiated from user input)

# new populate_bag method needs to be tested and then switched out with old method 
# switch order of topic/def, add newline (non trivial to implement bc of .yaml load / 
# python dict properties)

# populate_Struct method needs to be developed 

# add type checks for parameters 

# add support for sentry struct_def autogeneration (probably just some more msgpath variables)

# add more informative error catching 

# add support for unsized arrays (non trivial to implement)

# print information regarding which files were updated and how, when populate method is called
# include msg path 

# add value[1] to structFieldUnwrapped which is path from structField, and populate
# structs the same if they have equivalent paths

# continue to add support for special types

# may make sense to add a class to represent command line interface
# as populate methods become more complex 

import argparse
from collections import OrderedDict
import copy
import csv
import yaml 
import os
import random
import re
import subprocess
import pandas as pd
import tempfile


# A NamespaceTopics object represents a comprehensive list of rostopics for a 
# specific namespace for a given vehicle

# takes in a vehicle name and list of bagfiles for a certain namespace

# field 'name' is name of vehicle
# field 'df' is a pandas dataframe object with columns 
# of topics and types 

# gets called while initializing the bag field of a BagStructDefs object 

class NamespaceTopics():
    def __init__(self, vehicle, bagfiles):
        self.name = vehicle
        # importantly, the bagfiles parameter is a list of paths to rosbag files for dives across cruises
        # for a particular namespace
        totalSize = 0
        for b in bagfiles:
            print(os.path.getsize(b))
            totalSize += os.path.getsize(b)
        print('total bagfile size is ' + str(totalSize))

        self.df = self.convert_rosbaginfo_to_masterDf(bagfiles)

    # this function takes in the lists of topics and types of a namespace for a vehicle
    # and converts them into a pandas dataframe object 

    def generate_df(self, types, topics):
        df = pd.DataFrame({'Topics': topics, 'Types': types})
        return df
    
    # to do: 

    # some topics don't include name of vehicle 
    # i.e. topics in the globals namespace. the current parsing algorithm 
    # will then encounter a value error as there will be more topic types 
    # than topics, meaning generate_df will not be able to create a dataframe
    # since list objects are of different lengths
    # current fix is omitting globals namespace, but could also switch 
    # patternTopics to be patternTopicsNameOptional (though this switch is untested)

    # this function takes in contents of a txt file which is the result 
    # of running rosbag info on a bag file,
    # and parses out the types and topics as lists, returning two lists

    def parse_txt_file(self, contents):

        # Get section from file that contains topic and topic type info
        start_index = contents.find('topics:') + len('topics:')
        relevantSection = contents[start_index:]

        # Extract topics
        patternTopics = r'' + self.name + r'(?:(?!\d+\s*msg[s]?).)*?(?=\d+\s*msg[s]?)'
        patternTopicsNameOptional = r'(?:(?:' + self.name + r')?.*?(?=\d+\s*msg[s]?))'
        topics = re.findall(patternTopics, relevantSection)
        topics = [topic.strip() for topic in topics if topic.strip()]

        # Extract types 
        patternTypes =r'(?<=:\s)(.*)(?=\n)'
        types = re.findall(patternTypes, relevantSection)
        types = [re.sub(r'\s*\(\d+\s*connection(?:s)?\)', '', type.strip()) for type in types if type.strip()]
        
        
        return types, topics
    
     
    # this function takes in a list of paths to .bag files for a certain namespace
    # and returns a pandas dataframe object which consists of all the types and topics
    # from the .bag files (with duplicates removed)

    def convert_rosbaginfo_to_masterDf(self, bagfileList):
            masterDf = pd.DataFrame()
            txt_files = []
            root_dir = os.path.expanduser("~")
            tempDir = '/tmp'
            bagfileListLocal = []
            for bagFile in bagfileList:
                # rsync is used because performing ros operations 
                # is faster on local files than on vast
                rsyncCommand = ['rsync', '-av', bagFile, tempDir]
                subprocess.run(rsyncCommand)
                filename = os.path.basename(bagFile)
                copiedFilePath = os.path.join(tempDir, filename)
                bagfileListLocal.append(copiedFilePath)
                print('this is bagfile that just got copied ')
                print(bagFile)


            # for every bagfile for a certain namespace
            for bagFile in bagfileListLocal:
                # create a temporary file called temp_file
                with tempfile.NamedTemporaryFile(prefix='bag_txtfile_', mode='w', delete=False) as temp_file:
                    # append the path to that temp_file txt_files list 
                    txt_files.append(temp_file.name)
                    # command is rosbag info <bagfile> 
                    command = ['rosbag', 'info', bagFile]
                    with open(temp_file.name, 'r+') as file:
                        subprocess.run(command, stdout=file)
                        file.seek(0)
                        content = file.read()
                        # filter out 'empty' rosbags 
                        if 'topics:' in content:
                            # create a dataframe for this .txtfile, add it to masterDf, and then close file
                            types, topics = self.parse_txt_file(content)
                            curDf = self.generate_df(types, topics)
                            masterDf = pd.concat([masterDf, curDf])
        
            # remove temporary .txt files and rsynced bagfiles 
            for f in txt_files:
                os.remove(f)
            for b in bagfileListLocal:
                 if os.path.exists(b):
                    os.remove(b)

            masterDf.drop_duplicates(inplace=True)
            return masterDf
   
    def get_df(self):
        return self.df



# A BagStructDefs object holds the salient data structures and content
# which are needed to automate the 
# bag definition and struct definition from a .yaml file

# take in a vehiclename, ('sentry', 'alvin' 'jason'), and data
# which comes from the RosbagDiveData object

# field name is string representing vehicle name

# field data is RosbagDiveData object

# field yaml is the loaded vehiclename_extract.yaml file (in the form of a dictionary)

# field bags is a dictionary where every key is a namespace (i.e. 'sensors' or 'nav') 
# and every value is a pandas dataframe with all the topics and topic types for that namespace 

# field structs is a dictionary where every key is a namespace and 
# every value is a list of tuples with struct name and struct location directory 
# (i.e. [('Parameter_updates', 'dynamic_reconfigure/Config'), 
# ('Gyro', 'ds_sensor_msgs/Gyro'), ('Ctd', 'ds_sensor_msgs/Ctd')...]

# field structFields is a dictionary where every key is a struct (i.e. phinsbin.yaml) 
# and every value is a tuple with tuple[0] = struct msg location directory 
# (i.e. ds_sensor_msgs/PhinsStdbin3) and tuple[1] =  list of fieldtype/fieldname tuples
#  extracted from that location directory 
# (i.e. [('std_msgs/Header', 'header'), ('ds_core_msgs/DsHeader', 'ds_header'), ('uint32', 'nav_fields')...]

# field structFieldsUnwrapped is similar to structFields, but with nested path types recursively
# unwrapped so only primitive/non parsable types remain

# note: importantly, the true master list of topics/types is the csv
# whereas the BagStructDefs object fields are based on 
# on the RosbagDiveData, and can be manipulated to only 
# include data for certain cruises or dives based on command line argument 'mode'

class BagStructDefs():
    def __init__(self, vehiclename, vehDir, data):
        self.name = vehiclename
        self.data = data
        self.yaml = self.load_YamlExtract()
        self.bags = self.generate_BagsDict()
        self.structs = self.generate_StructsDict()
        self.structFields = self.generate_FieldsDict()
        self.structFieldsUnwrapped = self.generate_StructFieldsUnwrappedDict()
        
      
    def get_name(self):
        return self.name
      
    def get_data(self):
        return self.data

 

    # returns loaded vehiclename_extract.yaml file as dictionary
    def load_YamlExtract(self):
                vehicleName = self.get_name()
                # Get the root directory of the current user
                root_dir = os.path.expanduser("~")

                # Construct the base path by joining the root directory with the relative path to dsros_python
                basePath = os.path.join(root_dir, 'git', 'dslpp-git', 'dsros_python')

                extractPath = os.path.join(basePath, '{}/{}_extract.yaml'.format(vehicleName, vehicleName))
                
                while True:
                    try:
                        if os.path.exists(extractPath):

                            with open(extractPath, 'r') as file:
                                yamlDict = yaml.safe_load(file)
                            return yamlDict
                        else:
                            print('Please try again')
                            print(f"Tried {basePath}, didn't work\n")
                            print('Please provide the local path to the location of dsros_python, i.e. something like \n')
                            print(f"{basePath}")
                            basePath = input('Enter path: ')
                            extractPath = os.path.join(basePath, '{}/{}_extract.yaml'.format(vehicleName, vehicleName))
                            if os.path.exists(extractPath):
                                with open(extractPath, 'r') as file:
                                    yamlDict = yaml.safe_load(file)
                                return yamlDict
                    except:
                        print('Please try again')
                        continue

    
    def get_yaml(self):
        return self.yaml
    
    # to do: 
    # add a check for self.mode being 'dive', 
    # and if so, increase numBagSamples 

    # returns a dictionary where every key is a namespace and a value is a dataframe \
    # representing the topics and types for that namespace 
    def generate_BagsDict(self):
        dives = self.get_data().get_dives()
        name = self.get_name()
        
        yamlDict = self.get_yaml()

        # not super proud of this but globals is annoying me right now 
        if 'globals' in yamlDict:
            del yamlDict['globals']

        numBagSamples = 3
        intermediateDict = {}
        namespacetopicDict = {}
        for k in yamlDict.keys():
                namespaceBagfiles = []
                for d in dives:
                        # Get the list of files in the dive directory
                    files_in_dive = os.listdir(d)
                        # Filter the files to get only those that match the prefix 'k' and don't end in '.active'
                    matching_bagfiles = [file for file in files_in_dive if file.startswith(k) and not file.endswith(".active")]
                        
                        # Randomly select numBagSamples matching bag files (if available)
                    selected_bagfiles = random.sample(matching_bagfiles, min(numBagSamples, len(matching_bagfiles)))
                        
                        # Append the paths of the selected bag files to namespaceBagfiles
                    namespaceBagfiles.extend([os.path.join(d, bagfile) for bagfile in selected_bagfiles])

                # Add the list of selected bag files to the intermediate dictionary
                intermediateDict[k] = namespaceBagfiles
        for k in intermediateDict:
                print('this is k ' + str(k))
                n = NamespaceTopics(name, intermediateDict[k])
                masterDf = n.get_df()
                namespacetopicDict[k] = masterDf

        # update csv file which contains master list of topics and types
        for namespace, df in namespacetopicDict.items():
            csvPath = os.path.join('dsros_python', name, 'csv', f'{namespace}_topics_types.csv')
            # if there's stuff in the .csv and dataframe, update csv with stuff from the dataframe
            if os.path.exists(csvPath) and os.path.getsize(csvPath) > 0 and not df.empty:
                csvDf = pd.read_csv(csvPath)
                updatedDf = pd.concat([csvDf, df])
                updatedDf.drop_duplicates(inplace=True)
                updatedDf.to_csv(csvPath, index=False)
            # if there doesn't yet exist a csv, create it and populate 
            elif not os.path.exists(csvPath) and not df.empty:
                with open(csvPath, 'w', newline='') as csvfile:
                    df.to_csv(csvfile, index=False) 
            # empty df means do nothing
            else:
                pass

        return namespacetopicDict

    
    def get_bags(self):
        return self.bags
    
    # returns a dictionary where every key is a namespace
    # and every value is a list of tuples. each tuple contains a struct i.e. 'compass' 
    # and path to message type for that struct i.e. 'ds_sensor_msgs/Compass'
    def generate_StructsDict(self):
        namespaceBagDict = self.get_bags()
        name = self.get_name()
        namespaceStructDict = {}
        for key, value in namespaceBagDict.items():
            if not value.empty:
                topics = value['Topics'].tolist()
                types = value['Types'].tolist()
                messages = []
                for topic, type in zip(topics, types):
                    lastPart = topic.split('/')[-1].capitalize()
                    messages.append((lastPart, type))
                messagesNoDups = list(set(messages))
                namespaceStructDict[key] = messagesNoDups
            else:
                namespaceStructDict[key] = []
        
        return namespaceStructDict
    
    # takes in a field type and directory and returns a relative path
    # if field type and directory can form a valid relative path, returns
    # type without directory if not 
    def addRelativePath(self, fieldType, msgDir):
        potentialRelPath = os.path.join(os.path.expanduser('~'), '/opt', 'ros', 'noetic', 'share', msgDir, 'msg', fieldType + '.msg')
        if os.path.exists(potentialRelPath):
            return os.path.join(msgDir, fieldType)
        else:
            return fieldType
        

    # takes in path to a .msg def, returns list of tuples
    # which represent fieldtype/field for that .msg def 
    def parse_msg(self, input_file_path, structMsgDir):
        # seperates the boys from the men 
        # kidding
        # seperates the field from the field type 
        pattern = r'^\s*([\w/\[\]]+)\s+([\w/\[\]]+)'
        matches = []
        with open(input_file_path, 'r') as infile:
            for line in infile:
                if not line.startswith('#') and not line.isspace():
                    # Remove text after '#' within a line
                    line = re.sub(r'#.*', '', line)
                    # Remove constants
                    line = re.sub(r'.*=', '', line)
                    match = re.match(pattern, line)
                    if match:
                        fieldType = match.group(1)
                        if fieldType == 'Header':
                            fieldType = 'std_msgs/Header'
                        fieldType = self.addRelativePath(fieldType, structMsgDir)
                        field = match.group(2)
                        matches.append((fieldType, field))
        return matches
    
    # to do: 
    # add support for sentry specific msg paths

    # takes in a tuple where tuples[0] is equal to struct.yaml. 
    # returns list of fields for .msg type
    # based on preexisting .msg file 
    def extract_fields(self, tuple):
        miniPath = tuple[1]
        structMsgDir = '/'.join(miniPath.rsplit('/', 1)[:-1])
        msgFile = os.path.basename(miniPath) + '.msg'
        rootDir= os.path.expanduser("~")
        msgPathCustom = os.path.join(rootDir, 'ros', f'{self.get_name()}_ws', 'src', 'ds_msgs', structMsgDir, 'msg', msgFile)
        msgPathCommon = os.path.join(rootDir, '/opt', 'ros', 'noetic', 'share', structMsgDir, 'msg', msgFile)
  
        while True:
            try:
                if os.path.exists(msgPathCommon):
                    fieldTuples = self.parse_msg(msgPathCommon, structMsgDir)
                    return fieldTuples
                elif os.path.exists(msgPathCustom):
                    fieldTuples = self.parse_msg(msgPathCustom, structMsgDir)
                    return fieldTuples
                
                else:
                    print(f'Couldn\'t find path to msg {msgFile}\n')
                    msgPathUserProvided = input(f"Please provide an absolute path to the local location for the definition for {msgFile}, i.e. something like \n {msgPathCustom}")
                    fieldTuples = self.parse_msg(msgPathUserProvided, structMsgDir)
                    print(f"Using path {msgPathUserProvided} \n for {msgFile}")
                    return fieldTuples
            except:
                print(f"Please try again")
                continue
               

    
    # returns a dictionary where every key is a struct, i.e. 'fogest.yaml'
    # and every value is a tuple. tuple[0] is relative path to .msg def struct i.e. 
    # geometry_msgs/Vector3Stamped. tuple[1] is list of (potentially nested) tuples
    # with fieldtype, field i.e. [('std_msgs/Header', 'header'), ('geometry_msgs/Vector3', 'vector')]
    def generate_FieldsDict(self):
        namespaceStructDict = self.generate_StructsDict()
        structsList = []
        structFieldDict = {}
        for v in namespaceStructDict.values():
            structsList.extend(v)

        for t in structsList:
            structName = t[0].lower() + '.yaml'
            msgLoc = t[1]
            fieldTuples = self.extract_fields(t)
            structFieldDict[structName] = (msgLoc, fieldTuples)
        return structFieldDict

    def get_structs(self):
        return self.structs
    
    # deep copy since we don't want to risk mutatating field or .msg defs
    # during unwrapping
    def get_structFields(self):
        return copy.deepcopy(self.structFields)
    
    # takes in a string representing a fieldtype and
    # returns a tuple where tuple[0] is the field type without any array digits
    # and tuple[1] is a string reprsenting the array size, or '' if there was no array

    # note: pattern searches for digits, so field was 'Vector3[]' it would return
    # ('Vector3[]', '') but if field was 'Vector3[4]' it would return ('Vector3', '4')
    def processArrayNotation(self, field: str):
        pattern = r'^(.*)\[(\d+)\]$'
        match = re.match(pattern, field)
        if match:
            return (match.group(1), match.group(2))
        else:
            return (field, "")

    # takes in a list of (fieldtype, field) tuples and string which represents 
    # array size, empty if there is no array size 
    # returns a list where every tuple is duplicated arraySize times and a suffix is 
    # added to differentiate duplicates  

    # note: may want to switch outer and inner for loops 
    # depending on how data is entered / grouped   
    def addArraySuffixes(self, tupleList, arraySize : str):
        listWithSuffixes = []
        if arraySize == '':
            return tupleList
        else:
            for i in range(int(arraySize)):
                iList = []
                for c in tupleList:
                    fieldType = c[0]
                    fieldName = c[1]
                    newFieldType = self.processArrayNotation(fieldType)[0]
                    newFieldName = fieldName + '_' + str(i+1)
                    newTuple = (newFieldType, newFieldName)
                    iList.append(newTuple)
                listWithSuffixes.extend(iList)
            return listWithSuffixes
            
    # takes in a relative path to a .msg file (i.e. ds_sensor_msgs/PhinsStatus) 
    # and returns absolute path if path can be found with supplied parameters
    # '' if no path can be found 
    def createPath(self, miniPath):
        rootDir = os.path.expanduser('~')
        name = self.get_name()

        indvFirstDir = '/'.join(miniPath.rsplit('/', 1)[:-1])
        
        indvSecondPath = os.path.basename(miniPath)
        indvSecondPathNoDigits = self.processArrayNotation(indvSecondPath)[0]

        msgPathCustom = os.path.join(rootDir, 'ros', f'{name}_ws', 'src', 'ds_msgs', indvFirstDir, 'msg', indvSecondPathNoDigits + '.msg')
        msgPathCommon = os.path.join(rootDir, '/opt', 'ros', 'noetic', 'share', indvFirstDir, 'msg', indvSecondPathNoDigits + '.msg')
        if os.path.exists(msgPathCustom):
            return msgPathCustom
        elif os.path.exists(msgPathCommon):
            return msgPathCommon
        else:
            return ''   
             
    # takes in a single tuple i.e. (std_msgs/Header, header) or (float64, error_rate)
    # and performs unwrapping for the tuples, returning a single list which contains nested lists
    # depending on recursion depth of indvTuple field types
    def processIndvTuple(self, indvTuple):
        # 'cur' prefix is used to indicate a variables relates to indvTuple as opposed to the 
        # subfields of indvTuple
        pattern = r'^\s*([\w/\[\]]+)\s+([\w/\[\]]+)'
        curContainer = []
        # curMiniPath includes digits if they are there 
        curMiniPath = indvTuple[0]
        curName = indvTuple[1]
        relDir = '/'.join(curMiniPath.rsplit('/', 1)[:-1])
        # curAbsPath will not include digits 
        curAbsPath = self.createPath(curMiniPath)
        curArrayDigitString = self.processArrayNotation(curMiniPath)[1]
        print('cur mini path is ' + curMiniPath)
        print('cur name is ' + curName)
        print('cur rel dir is ' + relDir)
        print('cur abs path is ' + curAbsPath)
        print('cur digit array string is ' + curArrayDigitString)
        
        # if the indvTuple is nested (i.e. 'std_msgs/Header', 'header'), create containers 
        # for new subfields, populate containers, 
        # and then add each of these subfield containers to curContainer
        if bool(curAbsPath):
            with open(curAbsPath, 'r') as infile:
                for line in infile:
                    if not line.startswith('#') and not line.isspace():
                        # Remove text after '#' within a line
                        line = re.sub(r'#.*', '', line)
                        # Remove constants
                        line = re.sub(r'.*=', '', line)
                        match = re.match(pattern, line)
                        if match:
                            lineContainer = []
                            # special case to turn ('Header', 'header') into 
                            # (std_msgs/Header, 'header') to making unwrapping easier 
                            # later on
                            if match.group(1) == 'Header':
                                fieldType = 'std_msgs/Header'
                            else:
                                fieldType = match.group(1)
                            fieldType = self.addRelativePath(fieldType, relDir)
                            field = match.group(2)
                            # create the tuple 
                            lineTuple = (fieldType, curName + '.' + field)
                            lineContainer.append(lineTuple)
                            curContainer.append(lineContainer)
        # if indvTuple is not nested (i.e. 'string[4]', 'child_frame_id') create container, 
        # add tuple to container, and add container to curContainer
        else:
            unnestedTupleContainer = []
            unnestedTuple = (curMiniPath, curName)
            unnestedTupleContainer.append(unnestedTuple)
            curContainer.append(unnestedTupleContainer)
        #  at this point curContainer structure is something like
        #  where length = number of fields of indvTuple
        #  [[(... , ...)], [(... ,...)]]
        #  or 
        #  [[(... , ...)]]
        curSuffixedContainer = []
        for container in curContainer:
            suffixedContainer = self.addArraySuffixes(container, curArrayDigitString)
            curSuffixedContainer.append(suffixedContainer)

        # this function takes in a list of lists with suffix information 
        # and recurs, unwrapping any nested types
        # it outputs a final list of lists which does not contain any known nested types

        # to do:
        # recursion in rare cases produces excess brackets, somewhat trivial as overall list 
        # still matches desired length but would be good to fix either post or during recursion

        # note: may contain nested type if type contains unspecified array size
        # could fix by asking user for input but would introduce an undesired dependency 
        # on populate method and object instantation 
        def recurOnCurContainer(curSufContainer):
            processed_structure = []
                
            for item in curSufContainer:
                if isinstance(item, list):
                    processed_item = recurOnCurContainer(item)  
                    processed_structure.append(processed_item)
                elif isinstance(item, tuple):
                    
                    # true if primitive numbered type, i.e. 'uint8[16]'
                    numberedType = self.processArrayNotation(item[0])[1] != ''
                    # true if path, false if path with a non-numbered array
                    # i.e. geometry_msgs/Vector3 is true, geometry_msgs/Vector3[4]
                    # is true, geometry_msgs/Vector3[] is false 
                    # addRelPath spec allows '/' to be valid path indicator
                    pathType = '/' in item[0] and '[]' not in item[0]
                    if pathType or numberedType:
                        processedIndvTuple = self.processIndvTuple(item) 
                        processed_structure.append(processedIndvTuple)
                    else:
                        processed_structure.append(item)
            return processed_structure
        return recurOnCurContainer(curSuffixedContainer)

    # this function takes in a list of tuples (fieldType, field)
    # which come from the struct.yaml corresponding struct.msg def
    # it returns a list where every item in the list 
    # corresponds to a (fieldType, field)
    # tuple with all the fieldTypes 'unwrapped', meaning fieldTypes which are paths
    # to other .msg defs get recursively broken down into subsquent fieldTypes
    # until only primitive/special fieldTypes remain

    # ultimately emit one structTupleListofLists per struct.yaml
    def processStructTuples(self, structTuplesList):
        # say struct tuple five times fast 
        structTupleListofLists = []
        for structTuple in structTuplesList:
            print('this is individual tuple in processStructTuples')
            print(structTuple)
            structTupleListofLists.append(self.processIndvTuple(structTuple))     
        return structTupleListofLists


    
    # returns a dictionary where every key is
    # struct.yaml and every value is a list of lists of tuples with
    # path types unwrapped. 

    # same structure as structFields but more conducive to 
    # populating the /struct_defs folder 
    
    def generate_StructFieldsUnwrappedDict(self):
        structFieldDict = self.get_structFields()
        unwrappedDict = {}
        for key, value in structFieldDict.items():
            unwrappedDict[key] = self.processStructTuples(value[1])
        return unwrappedDict
    
    # deep copy because don't want to risk modifying dictionary during
    # populate method if populate method changes 
    def get_structFieldsUnwrapped(self):
        return copy.deepcopy(self.structFieldsUnwrapped)



    

# this class represents a RosbagDiveData object which can be instantiated by supplying 
# two parameters: vehiclename which is the string 'jason', 'alvin', or 'sentry', 
# and a dataDir which is the directory that holds all cruise information for the vehicle, 
# all cruise information for a specific cruise, and all rosbag files for a certain dive 
# if --mode arg is 'cumulative', 'cruise', or 'dive' respectively

# the RosbagDiveData object has three fields:
# field 'name' = vehicle name, string 'sentry' 'alvin' or 'jason'

# field 'mode' = 'cumulative' 'cruise' or 'dive'

# field 'dir' = directory path depending on mode, comes from --datadir command line arg 

# field 'cruises' = a representative sample of cruises which that vehicle has been on, 
# in the form of a list of paths to those cruises (empty if --mode is 'dive')

# field 'dives' = a representative sample of dives from those cruises, in the form of a 
# list of paths to rosbag directories for those dives 

class RosbagDiveData:
    def __init__(self, vehiclename: str, dataDir, mode):
        self.name = vehiclename
        self.mode = mode
        self.dir = dataDir
        self.cruises = self.create_cruiseDirList(dataDir)
        self.dives = self.create_diveDirList(self.cruises)


    def get_mode(self):
        return self.mode
    
    def get_dir(self):
        return self.dir
    
    # takes in a directory path to vehicle 
    # and uses ship prefixes and years to iterate through 
    # cruises for vehicle and return represenative list of cruises

    # note: sentry hierarchy is less than ideal in this regard:
    # there's a convention of year prefix instead of ship prefix 
    # which is unhelpful given that the directory is already oragnized by year

    def create_cruiseDirListCumulative(self, dataDir):
        cruiseDirList = []
        curDir = dataDir
        shipsJason = ['KM', 'TN']
        shipsAlvin = ['AT']
        shipsSentry = ['AT', 'TAN']
        # years for which there exists rosbag data
        yearsJasonAlvin = [2022, 2023]
        yearsSentry = [2021, 2022, 2023]

        if self.name == 'sentry':
            for y in yearsSentry:
                yearDir = os.path.join(curDir, str(y))
                if os.path.exists(yearDir) and os.path.isdir(yearDir):
                    # Get a list of subdirectories within the year directory
                    subdirs = os.listdir(yearDir)
                    subdirs = [subdir for subdir in subdirs if os.path.isdir(os.path.join(yearDir, subdir)) and subdir.startswith(str(y))]
                    # grab y-name directories and shipnameprefix directories
                    # Randomly select two subdirectories (if available) and append them to cruiseDirList
                    selected_subdirs = random.sample(subdirs, min(2, len(subdirs)))
                    cruiseDirList.extend([os.path.join(yearDir, subdir) for subdir in selected_subdirs])
        elif self.name in ('jason', 'alvin'):
            for y in yearsJasonAlvin:
                if self.name == 'jason':
                    ships = shipsJason
                if self.name == 'alvin':
                    ships = shipsAlvin
                for s in ships:
                    subdirs = [os.path.join(curDir, str(y), sdir) for sdir in os.listdir(os.path.join(curDir, str(y))) 
                               if os.path.isdir(os.path.join(curDir, str(y), sdir))]
                    # Filter subdirectories to keep only the ones that start with the current ship prefix (s)
                    subdirs_with_prefix = [subdir for subdir in subdirs if os.path.basename(subdir).startswith(s)]
                    # Randomly select one s from the subdirectories with the current ship prefix (s)
                    if subdirs_with_prefix:
                        chosen_s = random.choice(subdirs_with_prefix)
                        cruiseDirList.append(chosen_s)
                    else:
                        print(f"No directory found for {s} in year {y}")
        return cruiseDirList
    
    # takes in directory path supplied from command line
    # and returns a semi-random semi-intelligent list of cruises, returning
    # an empty list if --mode is 'dive
    def create_cruiseDirList(self, dataDir):
        mode = self.mode
        if mode == 'cumulative':
            cruisesList = self.create_cruiseDirListCumulative(dataDir)
        elif mode == 'cruise':
            cruisesList = [dataDir]
        elif mode == 'dive':
            cruisesList = []
        else:
            print('this should never get printed and if it does we\'re gonna need a bigger boat')
        return cruisesList
    

    # takes in list of cruises and returns a list of paths to directories 
    # containing .bag files for a certain dive 
    def create_diveDirList(self, cruises):
        if self.get_mode() == 'cumulative':
            numDives = 3
        elif self.get_mode() == 'cruise':
            numDives = 2
        elif self.get_mode() == 'dive':
            return [self.get_dir()]
        dives = []
        # randomly select three dives per cruise
        for c in cruises:
            print(c)
            # separate into cases because of disparity in directory structure between vehicles 
            if self.name == 'jason':
                # with jason directory structure, this leads you to list of dives which 
                # are containers for rosbag files
                rosbagsForDivesPath = os.path.join(c, 'Vehicle/Rawdata/Navest/rosbag')
                if os.path.exists(rosbagsForDivesPath) and os.path.isdir(rosbagsForDivesPath):
                    subdirectories = os.listdir(rosbagsForDivesPath)
                    chosenDives = random.sample(subdirectories, min(numDives, len(subdirectories)))
                    chosenDives = [os.path.join(c, 'Vehicle/Rawdata/Navest/rosbag', dive) for dive in chosenDives]
               
                    dives.append(chosenDives)
                 
            elif self.name == 'alvin':
                dives_path = c
                if os.path.exists(dives_path) and os.path.isdir(dives_path):
                    subdirectories = os.listdir(dives_path)
                    # filter out subdirectories to only include subdirectories that begin with 'AL'
                    filteredSubdirectories = [s for s in subdirectories if s.startswith('AL')]
                    # pick random sample of dives 
                    chosenDives = random.sample(filteredSubdirectories, min(numDives, len(filteredSubdirectories)))
                    # grab rosbag directory for those dives 
                    dives_with_rosbag = []
                    for dive in chosenDives:
                        rosbag_path = os.path.join(dives_path, dive, 'c+c/rosbag')
                        if os.path.exists(rosbag_path) and os.path.isdir(rosbag_path):
                            dives_with_rosbag.append(rosbag_path)
                    dives.append(dives_with_rosbag)
                dives.append(dives_with_rosbag)

            elif self.name == 'sentry':
                #chosenDives = random.sample(os.path.join(c, 'dives'), min(numDives, len(os.listdir(os.path.join(c, 'dives')))))
                chosenDivesSentry = os.listdir(os.path.join(c, 'dives'))
                filteredChosenDives = [d for d in chosenDivesSentry if d.startswith('sentry') and '-' not in d]
                divesRosbag = [os.path.join(c, 'dives', d, 'nav-sci', 'raw', 'rosbag') for d in filteredChosenDives]
                validDivesRosbag = [d for d in divesRosbag if os.path.exists(d)]
                dives.append(validDivesRosbag)

        # turn list of lists into list
        flattenedDives = [item for sublist in dives for item in sublist]

        return flattenedDives
    

    # Getter for the 'name' field
    def get_name(self):
        return self.name

    # Getter for the 'cruises' field
    def get_cruises(self):
        return self.cruises

    # Getter for the 'dives' field
    def get_dives(self):
        return self.dives


# this function takes all the nice constructions from the class objects 
# and uses them to actually create the bag definitions in the 
# dsros_python/vehiclename/bag_defs directory 
# must get called in order for /bag_def files to populate 

def populate_Bags(defs : BagStructDefs):

    name = defs.get_name()
    namespaceDict = defs.get_bags()
    yamlExtract = defs.get_yaml()
    

    # iterate through namespaces in extract.yaml file 
    for namespace, content in yamlExtract.items():
        if 'def' in content:
            namespaceFilename = content['def']
            root_dir = os.path.expanduser("~")
            namespacePath= os.path.join(root_dir, 'git', 'dslpp-git',
                                      'dsros_python', name, 'bag_defs', namespaceFilename)
            # grab the relevant dataframe
            if namespace in namespaceDict and not namespaceDict[namespace].empty:
                df = namespaceDict[namespace]
                topics = df['Topics'].tolist()
                types = df['Types'].tolist()

                # what the namespace.yaml file gets populated with
                newYamlContent ={}
                for topic, type in zip(topics, types):
                    lastPart = topic.split('/')[-1]
                    newYamlContent[lastPart] = {
                        'topic': topic,
                        'def': f"{lastPart}.yaml"

                    }
                # perform various checks for state of yaml file and then populate  
                if os.path.exists(namespacePath):
                    with open(namespacePath, 'r') as file:
                        isNonEmpty = bool(file.read().strip())
                        file.seek(0)
                        existingContent = yaml.safe_load(file)
                        if isNonEmpty and existingContent is not None:
                            existingContent.update(newYamlContent)
                    with open(namespacePath, 'w') as file:
                        if existingContent is not None and bool(existingContent):
                            yaml.safe_dump(existingContent, file)
                        else:
                            yaml.safe_dump(newYamlContent, file)
                else:
                    with open(namespacePath, 'w') as file:
                        yaml.safe_dump(newYamlContent, file)

# this function creates struct definitions 
# in the dsros_python/vehiclename/struct_defs directory 
# must get called in order for /struct_def files to populate
# calls for user input to assist in populating              
def populate_structs(defs : BagStructDefs):
    originalUnwrappedDict = defs.get_structFieldsUnwrapped()
    originalStructList = list(originalUnwrappedDict.keys())
    vehName = defs.get_name()
    
    # this function uses user input to create a list
    # of desired structs to populate /struct_defs with
    # returns list with desired structs
    def createProcessedStructList(unprocStructList : list):
        print("Please enter any structs you wish to omit from generation,")
        print("separated by a comma and then press enter, or just press enter if you do not wish to omit any structs.")
        while True:
            print("\nAvailable structs:")
            for struct in unprocStructList:
                print(struct)

            try:
                user_input = input("\nEnter structs to omit (comma-separated) or press enter: ")
                user_input = user_input.strip()  # Remove leading and trailing whitespace

                if not user_input or user_input == '':
                    print('Structs which will be generated:')
                    processedStructList = unprocStructList
                    [print(s) for s in processedStructList]
                    return processedStructList

                omitted_structs = [s.strip() for s in user_input.split(',')]
                    
                unrecognized_structs = [s for s in omitted_structs if s not in originalStructList]

                if unrecognized_structs:
                    raise ValueError("Input not recognized:", ", ".join(unrecognized_structs))
                    
                processedStructList = [struct for struct in originalStructList if struct not in omitted_structs]
                
                  
                
                return processedStructList
                
                
            except ValueError as e:
                print(e)
                continue
   
    # call createProcessStructList
    processedStructList = createProcessedStructList(originalStructList)

    # this function uses user input as well as known special
    # types to create a new dictionary with updated 
    # fieldTypes 

    def handleSpecialTypes(processedStructList, originalDictionary):
        processedUnwrappedDict = {}
            

        # takes in a nested list of tuples which represent the unwrapped
        # fieldtype, field for an entire struct, and creates a new
        # nested list with modificiations that account for special types 
        def processValue(structKey, nestedTupleList):
            processedValue = []
                
            for item in nestedTupleList:
                   


                # if list, recur until tuple 
                # i.e. unwrap it and recur 
                if isinstance(item, list):

                    newItem = processValue(structKey, item)
                    processedValue.append(newItem)
                        

                # if tuple, check all special cases and 
                # append tuples to processedValue accordingly
                elif isinstance(item, tuple):
                        

                    # rostime
                    if item[0] == 'time' and item[1] == 'header.stamp':
                        processedValue.append(('rostime', 'header.stamp'))

                    # bool or string type indicates potential special type
                    elif item[0] == 'bool' or item[0] == 'string':
                        newType1 = f"\n\nIdentified a possible special type in {item}) for struct '{structKey}'"
                        newType2 = f"Please enter a new type for '{item[0]}' (e.g., 'cell' or 'pwr_state')"
                        newType3 = f"or press Enter if '{item[0]}' is an acceptable type for '{item[1]}': "
                        newType = input(newType1 + '\n' + newType2 + '\n' + newType3 + '\n\n')
                        if newType != '':
                            processedValue.append((newType, item[1]))
                            print(f"Type {item[0]} changed to {newType}")
                        else:
                            processedValue.append(item)

                       

                    # tuple but not special 
                    else:
                        processedValue.append(item)
                
            return processedValue
                    
                    


        for key, value in originalDictionary.items():
            if key in processedStructList:
                print('Now generating struct defs for :' + key)
                processedUnwrappedDict[key] = processValue(key, value)
        return processedUnwrappedDict
           
    # call handleSpecialTypes
    processeedUnwrappedDict = handleSpecialTypes(processedStructList, originalUnwrappedDict)

        
    # takes in final processed dictionary which accounts
    # for user preferences and creates a dictionary where every key is a struct.yaml
    # and every value is a dictionary able to be loaded as a yaml file.
    # uses that dictionary to populate content in /struct_defs folder

    def populateStructDefFiles(procUnwrappedDict):
        dictForPopulating = {}
        
              
        # takes in list of lists representing 
        # unwrapped types for a yaml struct and 
        # outputs a .yaml friendly dict with those
        # types   
        def setYaml(value):
            print('printing set yaml')
            print(value)
            newYamlContent = {}
            for item in value:
                if isinstance(item, list):
                    newItem = setYaml(item)
                    if isinstance(newItem, dict):
                        newYamlContent.update(newItem)
                elif isinstance(item, tuple):
                    if item[0] =='FlaggedDouble':
                        print('flaggeddouble item')
                        print(item)
                        # special case which gets dealt with here 
                        # instead of other method because type doesn't
                        # need to be changed 
                        newYamlContent[item[1]] = {
                                'type': 'flagged',
                                'value': item[1] + '.value',
                                'valid': item[1] + '.valid'
                            }
                    else:
                        newYamlContent[item[1]] = {
                                'type': item[0],
                                'value': item[1]
                            }
                        
            return newYamlContent
            
            
        
        # actually populate 
        for key, value in procUnwrappedDict.items():
            dictForPopulating[key] = setYaml(value)
            newYamlContent = dictForPopulating[key]

            structFilename = key
            rootDir = os.path.expanduser("~")
            def getBasePath():         
                basePath = os.path.join(rootDir, 'git', 'dslpp-git', 'dsros_python')

                while True:
                    try:
                        if os.path.exists(basePath):
                            return basePath
                        else:
                            print(f"Please provide a path to the dsros_python directory on your machine")
                            print(f"i.e. something like \n {basePath}")
                            basePath = input('Enter path: ')
                            if os.path.exists(basePath):
                                return basePath
                            else:
                                raise FileNotFoundError()
                    except FileNotFoundError as e:
                        print(e)
                        print("Couldn't find path, try again")
                        continue
                        
                    
            basePath = getBasePath()
            structDefPath = os.path.join(basePath, vehName, 'struct_defs', structFilename)
            

            if os.path.exists(structDefPath):
                with open(structDefPath, 'r') as file:
                        isNonEmpty = bool(file.read().strip())
                        file.seek(0)
                        existingContent = yaml.safe_load(file)
                        if isNonEmpty and existingContent is not None:
                            existingContent.update(newYamlContent)
                with open(structDefPath, 'w') as file:
                    if existingContent is not None and bool(existingContent):
                        yaml.safe_dump(existingContent, file)
                    else:
                        yaml.safe_dump(newYamlContent, file)
            else:
                with open(structDefPath, 'w') as file:
                    yaml.safe_dump(newYamlContent, file)
    # call populateStructDefFiles 
    populateStructDefFiles(processeedUnwrappedDict)
                
            



# the main event if you will 
def main():
    parser = argparse.ArgumentParser(description='Create bag_defs and struct_defs based on _extract.yaml')
    parser.add_argument('--datadir', default='.', help='Directory which stores all data')
    parser.add_argument('--vehicle', choices=['jason', 'sentry', 'alvin'], help='Vehicle you wish to create defs for')
    parser.add_argument('--mode', default='cumulative', choices=['cumulative', 'cruise', 'dive'], help='Data you wish to create defs for')
    args = parser.parse_args()
    dataDir = args.datadir
    vehicleName= args.vehicle
    mode = args.mode
    data = RosbagDiveData(vehicleName, dataDir, mode)
    defs = BagStructDefs(vehicleName, dataDir, data)

    print("Cruises:")
    for cruise in data.get_cruises():
            print(cruise)
    print("Dives:")
    for dive in data.get_dives():
            print(dive)
    print('\n\nPrinting bag def info')
    for key, value in defs.get_bags().items():
      print(f"\nNamespace: {key}")
      print(value.head(500))
    print('\n\nPrinting struct def info')
    for key, value in defs.get_structs().items():
        print(f"\nNamespace: {key}")
        print(value)
    print('\n\nPrinting struct field info')
    for key, value in defs.get_structFields().items():
        print(f"\nStruct: {key}")
        print('this is length of struct field dict ' + str(len(value[1])))
        print(f"Type: {value[0]}")
        print(f"Fields: {value[1]}")
    print('\n\nThis is complete set of field types for this configuration')
    fieldSet = set()
    for key, value in defs.get_structFields().items():
        for fields in value[1]:
            fieldSet.add(fields[0])
    print(fieldSet)
    print('\n\nPrinting struct fields fully unwrapped')
    for key, value in defs.get_structFieldsUnwrapped().items():
        print(f"\n\nStruct:{key}")
        print('this is length of list of lists: ' + str(len(value)))
        print(f"\n\nUnwrapped:")
        print(value)
    populate_Bags(defs)
    populate_structs(defs)

if __name__ == '__main__':
    main()
    



    
