'''

################################################################################
############################### MAIN SCRIPT ####################################

# This script is designed to initialise and run a server which displays graphs
# using the data from the QA database.

# Use this while developing a new script without having to run through the user
# interface and display all the tabs built into main.py.

# Steps:
#   1)  Line 59 - Import your function here using the example format:
#       (from scripts.filename import Function_Name)
#   2)  Line 113 - Give the code the location of the database you are using.
#       NB: Always use a non-live copy of the database for development work
#   3)  Line 136 - Create the tab that will be displayed by the server using the
#       example format:
#       tab1 = Function_Name(conn)

# NB: In order to import the scripts in the way used here there must be an empty
# file called __init__.py in the scripts folder (https://stackoverflow.com/questions/279237/import-a-module-from-a-relative-path/48468292#48468292)

################################################################################
################################################################################

'''



################################################################################
####################### IMPORT LIBRARIES AND SCRIPTS ###########################

print('\nImporting libraries...')

# Import time and start a timer to do some checks of how long this code is
# taking to run.
import time
start = time.time()

# Import some basic tools from easygui to allow for user interface
from easygui import fileopenbox

# Import pandas, which is used for datamanagement and the creation of
# dataframes.
import pandas as pd

# Import os to allow manipluation of filepaths etc ????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????
import os

# Import some basic stuff from bokeh. Just need enough to be able to mainpulate
# the tabs etc. as most of the creation of the graphs will be done within the
# individual tab scripts.
from bokeh.io import curdoc
from bokeh.models.widgets import Tabs

# Import the tab scripts. Each script creates exactly one tab. (As mentioned
# earlier if there are problems importing these scripts then make sure that
# there is an empty file called __init__.py in the scripts folder).
from scripts.image_analysis import ColorMapper

# Import pypyodbc as this is how conections to the database can be achieved.
import pypyodbc

# Import some other bokeh and tornado libraries that will allow for the creation
# and running of the server.
from bokeh.server.server import Server
from bokeh.application.handlers import FunctionHandler
from bokeh.application import Application
from tornado.ioloop import IOLoop
from functools import partial

###### Start of patch!
###### Need a fix for running the Tornado Server in Python 3.8 on Windows. This
###### piece of code seems to allow it to run correctly (something about
###### needing to change a Windows default?):
######          https://github.com/tornadoweb/tornado/issues/2751
######          https://github.com/tornadoweb/tornado/issues/2608
import sys
import asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
###### End of patch!

# With the libraries imported run a check to find out how long it took.
endlib = time.time()
print('\nLibraries loaded in: ' + str(endlib - start) + 'sec')

################################################################################




################################################################################
################################################################################

def produce_doc(doc):

    ############################################################################
    ######################## CREATE EACH OF THE TABS ###########################

    # Going to make 3 tabs. These will be identical to start with but I think
    # by runnning it 3 times it will be possible to assess 3 different images
    # at the same time.

	# Select the image to be analysed
    filelocation = fileopenbox(title='Select image', msg='Please select image')

    tab1 = ColorMapper(filelocation)
    tab2 = ColorMapper(filelocation)
    tab3 = ColorMapper(filelocation)
    tabs = Tabs(tabs = [tab1, tab2, tab3])

    # Put all of the tabs into the doccument
    doc.add_root(tabs)

    # With the tabs made run a check to find out how long it took.
    endconn = time.time()
    print('\nTabs made in: ' + str(endconn - endlib) + 'sec')

    return doc





################################################################################
######################### DEFINE MAIN FUNCTION #################################

# This function creates a server and opens it in a web browser. It calls the
# produce_doc function defined above, opening this document (containing the
# bokeh graphs) within the browser.

# This code was originally written by VR (Bill).
# Commented and altered by CB (Christian).

################################################################################
################################################################################

def main():

    print('\nPreparing a bokeh application.')

    ############################################################################
    ####################### DEFINE VARIABLES FOR SERVER ########################

    # From what I (CB) understand this is a way to build the bokeh server within
    # the programme without needing to use the bokeh server command line tool.
    # https://docs.bokeh.org/en/latest/docs/reference/application/handlers/function.html
    # Start an Input/Output Loop. (Specifically a Tornado asynchronous I/O Loop)
    io_loop = IOLoop.current()
    # Define port for server
    port = 5001
    # Create kwargs which will be fed into the server function as keyworded
    # arguments.
    kwargs =    {
                'io_loop': io_loop,
                'port': port,
                }
    # Define the application using the bokeh application function handler.
    app = Application(FunctionHandler(produce_doc))


    ############################################################################
    ############################ CREATE THE SERVER #############################

    # Define the server
    # http://matthewrocklin.com/blog/work/2017/06/28/simple-bokeh-server
    server = Server({'/' : app},  **kwargs)
    # Start running the server
    server.start()
    print('\nOpening Bokeh application on http://localhost:5001/')
    # Display the server
    server.show('/')
    # Start the Input/Output Loop
    io_loop.start()





################################################################################
############################### RUN MAIN #######################################

main()
