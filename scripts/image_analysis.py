################################################################################
############################## IMPORT LIBRARIES ################################

# Might want this for line profiles?
from scipy.ndimage import map_coordinates
import math
import random

from easygui import diropenbox, fileopenbox

# pandas and numpy for data manipulation
import pandas as pd
import numpy as np

# datetime for setting up DateRangeSlider with generic values
from datetime import date

# functions from bokeh
from bokeh.plotting import figure
from bokeh.models import (CategoricalColorMapper, HoverTool, BoxZoomTool,
	PanTool, WheelZoomTool, ResetTool, ColumnDataSource, Panel, CrosshairTool,
	FuncTickFormatter, SingleIntervalTicker, LinearAxis, CustomJS,
	DatetimeTickFormatter, BasicTickFormatter, NumeralTickFormatter, Arrow,
	NormalHead, OpenHead, VeeHead, Label, PointDrawTool, Range1d, FileInput)
from bokeh.models.widgets import (CheckboxGroup, Slider, RangeSlider,
	Tabs, CheckboxButtonGroup, Dropdown, TableColumn, DataTable, Select,
	DateRangeSlider)
from bokeh.layouts import column, row, WidgetBox, layout
from bokeh.palettes import Category20_16, turbo, Colorblind, Spectral11
import bokeh.colors
from bokeh.io import output_file, show
from bokeh.transform import factor_cmap, factor_mark
from bokeh.events import Pan, PlotEvent, MouseWheel

import base64
import io

# PIL for importing TIF file
from PIL import Image

# https://discourse.bokeh.org/t/updating-image-or-figure-with-new-x-y-dw-dh/1971/4

################################################################################
################################################################################

class BoxZoom:
	def __init__(self, x_range_start, x_range_end, y_range_start, y_range_end):
		self.x_range_start = x_range_start
		self.x_range_end = x_range_end
		self.y_range_start = y_range_start
		self.y_range_end = y_range_end
		self.df = {	'x_range_start': self.x_range_start,
					'x_range_end,': self.x_range_end,
					'y_range_start': self.y_range_start,
					'y_range_end,': self.y_range_end}


# Create a dictionary containing the image array
def create_dict_image(filelocation):

	# Read in image and turn into an array
	arr1 = np.array(Image.open(filelocation))
	# Flip the array because Bokeh reads the array in from the bottom left
	# corner but the image
	arr1 = np.flipud(arr1)
	# Get the width and height of the array. Annoyingly pixels are accessed by
	# (y,x) coordinates.
	(dh1, dw1) = arr1.shape

	# Create a dictionary with this information
	dict_image = {}
	dict_image['image'] = [arr1]
	dict_image['dh1'] = [dh1]
	dict_image['dw1'] = [dw1]

	return dict_image





# Create a profile
def create_prof(dict_image, x_prof_start, x_prof_end, y_prof_start, y_prof_end):
	# Calculate how long the line is (hypotenuse eqn.)
	prof_length = math.sqrt((x_prof_start-x_prof_end)**2
		+ (y_prof_start-y_prof_end)**2)
	# Sample roughly every 0.1 pixels which should be plenty.
	prof_sample = int(prof_length/0.1)
	# Create a list of evenly spaced coordinates
	x_prof_sample = np.linspace(x_prof_start, x_prof_end, prof_sample)
	y_prof_sample = np.linspace(y_prof_start, y_prof_end, prof_sample)
	# Create a list of pixel values at these coordinates (interpolating where
	# needed). map_coordinates an interpolation thing. Come back to this later?
	z_prof_sample = map_coordinates(dict_image['image'][0],
		np.vstack((y_prof_sample, x_prof_sample)))
	# Normalise to the max value in the profile
	z_prof_sample = z_prof_sample*(100/(max(z_prof_sample)))
	# Make it into a dictionary where 'x' is the 'length' dimension and 'y' is
	# the pixel value.
	dict_prof = {'x': list(range(0, len(z_prof_sample))), 'y': z_prof_sample}
	# Turn it into a dataframe and return
	df_prof = pd.DataFrame(dict_prof)

	# Also make a dataframe for the profile points
	df_prof_points = pd.DataFrame({	'x': [x_prof_start, x_prof_end],
									'y': [y_prof_start, y_prof_end]})

	return df_prof, df_prof_points





def ColorMapper(filelocation):

	############################################################################
	############################## CHARMANDER ##################################

	# Quick plot of charmander image to check file orientations are done
	# correctly. Also later for fun.
	file_charmander = 'O:\\protons\\Work in Progress\\Christian\\Python\\Graphing Code\\CB Version\\New Ideas\\Charmander.png'
	arr_charmander=np.array(Image.open(file_charmander))
	arr_charmander=np.flipud(arr_charmander)
	p_charmander = figure()
	p_charmander.plot_height = 400
	p_charmander.plot_width = 400
	p_charmander.image_rgba(image=[arr_charmander], x=[0], y=[0], dw=[1], dh=[1])

	############################################################################
	############################################################################




	############################################################################
	######################### START CREATING DATASETS ##########################

	# Create the sub dataframe (limited by the displayed adate and energy)
	# Create the dictionary (limited to just one row of the sub dataframe and
	# includes the image array
	dict_image = create_dict_image(filelocation)

	# Create the column data source
	src_image = ColumnDataSource(dict_image)


	############################################################################
	############################################################################





	############################################################################
	######################## SET SOME STARTING VALUES ##########################

	# Set some values for the start and end x and y for the line profile we'll
 	# make later. (For simplicity we're going to plot a +ve diagonal over the
	# topleft (tl) spot)
	x_range_start = 0
	x_range_end = 100
	y_range_start = 0
	y_range_end = 100
	box_zoom = BoxZoom(x_range_start, x_range_end, y_range_start, y_range_end)

	############################################################################
	############################################################################





	############################################################################
	######################### WORK OUT A LINE PROFILE ##########################

	# This should work out the pixel values along an arbitary line profile.
	# NB: It does some sort of interpolation between pixels that should probably
	# be looked at in some more detail.

	x_prof_start = 0
	x_prof_end = 100
	y_prof_start = 0
	y_prof_end = 100

	df_prof, df_prof_points = create_prof(dict_image, x_prof_start, x_prof_end,
		y_prof_start, y_prof_end)
	src_prof = ColumnDataSource(df_prof.to_dict(orient='list'))
	src_prof_points = ColumnDataSource(df_prof_points.to_dict(orient='list'))

	# Create the profile plot
	p_prof = figure()
	p_prof.plot_height = 300
	p_prof.plot_width = 800
	p_prof.line(source=src_prof, x='x', y='y')
	# Add a couple of tools
	p_prof.add_tools(CrosshairTool(), HoverTool(tooltips=[('X-Axis', '@x'),
		('Y-Axis', '@y')], mode='hline', line_policy='nearest'))

	# Going to add a datatable to display the position of these two points as
	# well. (Apparently this is done by make a datatable widget?)
	columns_prof_points = [TableColumn(field='x', title='x-position', width = 100),
           TableColumn(field='y', title='y-position', width = 100)]
	datatable_prof_points = DataTable(source=src_prof_points,
		columns=columns_prof_points, width=600, height=100, editable=True,
		selectable='checkbox')

	############################################################################
	############################################################################






	############################################################################
	########################### CREATE THE MAIN PLOT ###########################

	##### 1)
	# Create the main image with some basic tools and the underlying image
	# painted in.
	p_main = figure(tools=[PanTool(), WheelZoomTool(),
		BoxZoomTool(match_aspect=True), ResetTool()],
		tooltips=[('x', '$x'), ('y', '$y'), ('value', '@image')],)
	p_main.plot_height = round(dict_image['dh1'][0]/2)
	p_main.plot_width = round(dict_image['dw1'][0]/2)
	p_main.image(source=src_image, image='image', x=0, y=0, dw='dw1', dh='dh1',
		palette="Spectral11", level="image")

	##### 2)
	# Add the parts needed to make the line profile work (i.e. the line, some
	# points on either end of the line and a tool to manipulate it)
	p_main.line(source=src_prof_points, x='x', y='y', line_width=2,
		color='black')
	# Circles done in this way so it can be manipulated by the PointDrawTool
	c1 = p_main.circle(source=src_prof_points, x='x', y='y', color='black',
		fill_alpha=0.5, size=12)
	p_main.add_tools(PointDrawTool(renderers=[c1], num_objects=2))

	##### 3)                                                                        Need to come back to this when decide how to draw the boxes
	# Add the box on the main image that show the viewing ranges of the
	# smaller one
	dict_zoombox = {}
	dict_zoombox['x'] = [box_zoom.x_range_start, box_zoom.x_range_end,
		box_zoom.x_range_end, box_zoom.x_range_start, box_zoom.x_range_start]
	dict_zoombox['y'] = [box_zoom.y_range_start, box_zoom.y_range_start,
		box_zoom.y_range_end, box_zoom.y_range_end, box_zoom.y_range_start]

	df_zoom = pd.DataFrame(dict_zoombox)
	src_zoom = ColumnDataSource(df_zoom.to_dict(orient='list'))

	p_main.line(source=src_zoom, x='x', y='y', line_width=2, color='firebrick')



	############################################################################
	#################### CREATE THE SMALL VIEWING WINDOW #######################

	# Initialise all the figures and put in a list to iterate over. Lock the
	# aspect ratio of the box tool so it doesn't end up stretching the images.
	p_zoom = figure(tools=[PanTool(), WheelZoomTool(),
		BoxZoomTool(match_aspect=True), ResetTool()])

	# Set plot parameters and add glyphs and image
	p_zoom.plot_height = round(400)
	p_zoom.plot_width = round(400)
	p_zoom.x_range.start = box_zoom.x_range_start
	p_zoom.x_range.end = box_zoom.x_range_end
	p_zoom.y_range.start = box_zoom.y_range_start
	p_zoom.y_range.end = box_zoom.y_range_end

	p_zoom.image(image='image', source=src_image, x=0, y=0, dw='dw1', dh='dh1',
		palette='Spectral11', level='image')
	p_zoom.line(source=src_prof_points, x='x', y='y', line_width=2,
		color='black')
	c1 = p_zoom.circle(source=src_prof_points, x='x', y='y', color='black',
		fill_alpha=0.5, size=12)
	p_zoom.add_tools(PointDrawTool(renderers=[c1], num_objects=2))




	file_input = FileInput(accept='.bmp')





	############################################################################
	############################## SET THE LAYOUT ##############################

	column1 = column(row(p_charmander, p_zoom), p_prof, datatable_prof_points)
	column2 = column(p_main, file_input)
	layout = row(column1, column2)



	# Can probably make this much quicker by making seperate callbacks for each
	# individual image. It will be a lot of code but that way it doesn't have to
	# do a full loop to check if any others have changed.
	#
	# Might be that actually it's the rewritting of the display which is the
	# rate determining step. So by keeping the loop to just rewriting the
	# dictionary this might keep it quick enough?
	def callback_range(attr, old, new):

		box_zoom = BoxZoom(p_zoom.x_range.start, p_zoom.x_range.end,
			p_zoom.y_range.start, p_zoom.y_range.end)

		dict_zoombox['x'] = [box_zoom.x_range_start, box_zoom.x_range_end,
			box_zoom.x_range_end, box_zoom.x_range_start, box_zoom.x_range_start]
		dict_zoombox['y'] = [box_zoom.y_range_start, box_zoom.y_range_start,
			box_zoom.y_range_end, box_zoom.y_range_end, box_zoom.y_range_start]


		df_zoom = pd.DataFrame(dict_zoombox)
		src_zoom.data = df_zoom.to_dict(orient='list')

		return


	p_zoom.x_range.on_change('start', callback_range)
	p_zoom.x_range.on_change('end', callback_range)
	p_zoom.y_range.on_change('start', callback_range)
	p_zoom.y_range.on_change('end', callback_range)


	def callback_prof (attr, old, new):

		# I think src_prof.data already is a dictionary but just to make sure
		dict_prof_points = src_prof_points.data
		dict_image = src_image.data

		x_prof_start, x_prof_end = dict_prof_points['x']
		y_prof_start, y_prof_end = dict_prof_points['y']
		x_prof_start = float(x_prof_start)
		x_prof_end = float(x_prof_end)
		y_prof_start = float(y_prof_start)
		y_prof_end = float(y_prof_end)

		df_prof, df_prof_points = create_prof(dict_image, x_prof_start,
			x_prof_end, y_prof_start, y_prof_end)

		src_prof.data = df_prof.to_dict(orient='list')

		return

	src_prof_points.on_change('data', callback_prof)
	datatable_prof_points.on_change('source', callback_prof)



	def callback_file_input (attr, old, new):

		decoded_image = base64.b64decode(file_input.value)
		arr1 = np.array(Image.open(io.BytesIO(decoded_image)))
		arr1 = np.flipud(arr1)
		(dh1, dw1) = arr1.shape

		dict_image = {}
		dict_image['image'] = [arr1]
		dict_image['dh1'] = [dh1]
		dict_image['dw1'] = [dw1]

		src_image.data = dict_image

		return

	file_input.on_change('value', callback_file_input)



	# Return the panel

	return Panel(child = layout, title = 'ColorMapper')















#
