################################################################################
############################## IMPORT LIBRARIES ################################

# Might want this for line profiles?
from scipy.ndimage import map_coordinates
import math
import random

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
	NormalHead, OpenHead, VeeHead, Label, PointDrawTool, Range1d)
from bokeh.models.widgets import (CheckboxGroup, Slider, RangeSlider,
	Tabs, CheckboxButtonGroup, Dropdown, TableColumn, DataTable, Select,
	DateRangeSlider)
from bokeh.layouts import column, row, WidgetBox, layout
from bokeh.palettes import Category20_16, turbo, Colorblind, Spectral11
import bokeh.colors
from bokeh.io import output_file, show
from bokeh.transform import factor_cmap, factor_mark
from bokeh.events import Pan, PlotEvent, MouseWheel

# PIL for importing TIF file
from PIL import Image

# https://discourse.bokeh.org/t/updating-image-or-figure-with-new-x-y-dw-dh/1971/4

################################################################################
################################################################################

# Define the expected position of the spots

class SpotParameters:
	def __init__(self, x_pos_exp, y_pos_exp, range, x_pos_meas, y_pos_meas):
		self.x_pos_exp = x_pos_exp
		self.y_pos_exp = y_pos_exp
		self.x_range_start = x_pos_exp - range
		self.x_range_end = x_pos_exp + range
		self.y_range_start = y_pos_exp - range
		self.y_range_end = y_pos_exp + range
		self.x_pos_meas = x_pos_meas
		self.y_pos_meas = y_pos_meas
		self.df = {	'x_pos_exp': self.x_pos_exp,
					'y_pos_exp': self.y_pos_exp,
					'x_range_start': self.x_range_start,
					'x_range_end,': self.x_range_end,
					'y_range_start': self.y_range_start,
					'y_range_end,': self.y_range_end,
					'x_pos_meas': self.x_pos_meas,
					'y_pos_meas': self.y_pos_meas}


# Going to have 2 things to indicate what image needs to be displayed
# accesable through some select widgets.
# 	1) The adate (defaults most recent)
# 	2) The energy (defaults )
def create_df(conn):

	# Use the connection passed to the function to read the data into a
	# dataframe via an SQL query.
	df = pd.read_sql('SELECT * FROM [Spot Profile]', conn)

	# Delete empty rows where the data is very important to have
	df = df.dropna(subset=['adate'])
	df = df.dropna(subset=['energy'])

	# Turn 'adate' into datetime.
	df.loc[:,'adate'] = pd.to_datetime(df.loc[:,'adate'], dayfirst=True)

	return df



def create_dict_image(df, adate=None, energy=None):

	# This will copy the dataframe and then cut out everything but the
	# adate and energy that are selected (or a default option of the most
	# recent adate and the lowest energy)
	Sub_df = df.copy()

	if adate != None:
		default_adate = [adate]
		Sub_df = Sub_df[Sub_df['adate'].isin(default_adate)]
	else:
		default_adate = [Sub_df['adate'].max()]
		Sub_df = Sub_df[Sub_df['adate'].isin(default_adate)]

	if energy != None:
		default_energy = [energy]
		Sub_df = Sub_df[Sub_df['energy'].isin(default_energy)]
	else:
		default_energy = [Sub_df['energy'].max()]
		Sub_df = Sub_df[Sub_df['energy'].isin(default_energy)]

	# Reset the index to 0
	Sub_df = Sub_df.reset_index(drop=True)
	# Turn into a dictionary as can't store an array in a dataframe
	dict_image = Sub_df.to_dict(orient='list')

	# Make sure that all of the file locations are the same for the same
	# adate and energy. (This should be the case but flag error otherwise)
	if len(dict_image['image file location']) > 0:
		result = all(elem == dict_image['image file location'][0]
			for elem in dict_image['image file location'])
		if not result:
			print('\nNot all image file locatons are the same for the ' \
				'following: \nADate = ' + str(default_adate[0]) +
				'\nEnergy = ' + str(default_energy[0]))
			exit()

	# Loop through the dictionary and just take the first element from the
	# lists (as all the elements will be the same)
	for key in dict_image:
		dict_image[key] = [dict_image[key][0]]

	# Read in image and turn into an array
	arr1 = np.array(Image.open(dict_image['image file location'][0]))
	# Flip the array because Bokeh reads the array in from the bottom left
	# corner but the image
	arr1 = np.flipud(arr1)
	# Get the width and height of the array. Annoyingly pixels are accessed by
	# (y,x) coordinates.
	(dh1, dw1) = arr1.shape

	# Add to the dictionary
	dict_image['image'] = [arr1]
	dict_image['dh1'] = [dh1]
	dict_image['dw1'] = [dw1]

	return Sub_df, dict_image



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



def create_spot_parameters(Sub_df):

	viewing_range = 40

	spot_tl = SpotParameters(600, 800, viewing_range, Sub_df['x-position'][0], Sub_df['y-position'][0])
	spot_tc = SpotParameters(800, 800, viewing_range, Sub_df['x-position'][1], Sub_df['x-position'][1])
	spot_tr = SpotParameters(1000, 800, viewing_range, Sub_df['x-position'][2], Sub_df['x-position'][2])
	spot_ml = SpotParameters(600, 600, viewing_range, Sub_df['x-position'][3], Sub_df['x-position'][3])
	spot_mc = SpotParameters(800, 600, viewing_range, Sub_df['x-position'][4], Sub_df['x-position'][4])
	spot_mr = SpotParameters(1000, 600, viewing_range, Sub_df['x-position'][5], Sub_df['x-position'][5])
	spot_bl = SpotParameters(600, 400, viewing_range, random.gauss(600, 5), random.gauss(400, 5))
	spot_bc = SpotParameters(800, 400, viewing_range, random.gauss(800, 5), random.gauss(400, 5))
	spot_br = SpotParameters(1000, 400, viewing_range, random.gauss(1000, 5), random.gauss(400, 5))

	spot_parameters = [spot_tl, spot_tc, spot_tr, spot_ml, spot_mc, spot_mr,
		spot_bl, spot_bc, spot_br]
	spot_dict = [spot_tl.dict, spot_tc.dict, spot_tr.dict, spot_ml.dict,
		spot_mc.dict, spot_mr.dict, spot_bl.dict, spot_bc.dict, spot_br.dict]
	spot_positions = ['tl', 'tc', 'tr', 'ml', 'mc', 'mr', 'bl', 'bc', 'br']

	return spot_parameters, spot_positions












def ColorMapper(conn):

	############################################################################
	############################## CHARMANDER ##################################

	# Quick plot of charmander image to check file orientations are done
	# correctly. Also later for fun.
	file_charmander = 'O:\\protons\\Work in Progress\\Christian\\Python\\Graphing Code\\CB Version\\New Ideas\\Charmander.png'
	arr_charmander=np.array(Image.open(file_charmander))
	arr_charmander=np.flipud(arr_charmander)
	p_charmander = figure()
	p_charmander.plot_height = 300
	p_charmander.plot_width = 300
	p_charmander.image_rgba(image=[arr_charmander], x=[0], y=[0], dw=[1], dh=[1])

	############################################################################
	############################################################################






	############################################################################
	######################### START CREATING DATASETS ##########################

	# Create the main dataframe (limited by the displayed adate and energy)
	df = create_df(conn)

	# Create the sub dataframe (limited by the displayed adate and energy)
	# Create the dictionary (limited to just one row of the sub dataframe and
	# includes the image array
	Sub_df, dict_image = create_dict_image(df)

	# Create the column data source
	src_image = ColumnDataSource(dict_image)

	# Use the class to store data on the spots
	spot_parameters, spot_positions = create_spot_parameters(Sub_df)

	############################################################################
	############################################################################





	############################################################################
	######################## SET SOME STARTING VALUES ##########################

	# Set some values for the start and end x and y for the line profile we'll
 	# make later. (For simplicity we're going to plot a +ve diagonal over the
	# topleft (tl) spot)
	x_prof_start = 570
	x_prof_end = 630
	y_prof_start = 770
	y_prof_end = 830

	############################################################################
	############################################################################





	############################################################################
	######################### WORK OUT A LINE PROFILE ##########################

	# This should work out the pixel values along an arbitary line profile.
	# NB: It does some sort of interpolation between pixels that should probably
	# be looked at in some more detail.

	df_prof, df_prof_points = create_prof(dict_image, x_prof_start, x_prof_end,
		y_prof_start, y_prof_end)
	src_prof = ColumnDataSource(df_prof.to_dict(orient='list'))
	src_prof_points = ColumnDataSource(df_prof_points.to_dict(orient='list'))

	# Create the profile plot
	p_prof = figure()
	p_prof.plot_height = 300
	p_prof.plot_width = 600
	p_prof.line(source=src_prof, x='x', y='y')
	# Add a couple of tools
	p_prof.add_tools(CrosshairTool(), HoverTool(tooltips=[('X-Axis', '@x'),
		('Y-Axis', '@y')], mode='hline', line_policy='nearest'))

	# Going to add a datatable to display the position of these two points as
	# well. (Apparently this is done by make a datatable widget?)
	columns_prof_points = [TableColumn(field="x", title="x-position", width = 100),
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
		tooltips=[("x", "$x"), ("y", "$y"), ("value", "@image")],)
	p_main.plot_height = round(dict_image['dh1'][0]/2)
	p_main.plot_width = round(dict_image['dw1'][0]/2)
	p_main.image( source=src_image, image='image', x=0, y=0, dw='dw1', dh='dh1',
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

	##### 3)
	# Add the boxes on the main image that show the viewing ranges of the
	# smaller ones
	spot_dict = {}
	for i in range(0, len(spot_positions)):
		spot_dict['x_'+spot_positions[i]] = [spot_parameters[i].x_range_start,
			spot_parameters[i].x_range_end, spot_parameters[i].x_range_end,
			spot_parameters[i].x_range_start, spot_parameters[i].x_range_start]
		spot_dict['y_'+spot_positions[i]] = [spot_parameters[i].y_range_start,
			spot_parameters[i].y_range_start, spot_parameters[i].y_range_end,
			spot_parameters[i].y_range_end, spot_parameters[i].y_range_start]

	df_spot = pd.DataFrame(spot_dict)
	src_spot = ColumnDataSource(df_spot.to_dict(orient='list'))

	for i in range(0, len(spot_positions)):
		p_main.line(source=src_spot, x='x_'+spot_positions[i],
			y='y_'+spot_positions[i], line_width=2, color='firebrick')



	############################################################################
	#################### CREATE THE SMALL VIEWING WINDOWS ######################

	# Initialise all the figures and put in a list to iterate over. Lock the
	# aspect ratio of the box tool so it doesn't end up stretching the images.
	p_tl = figure(tools=[PanTool(), WheelZoomTool(),
		BoxZoomTool(match_aspect=True), ResetTool()])
	p_tc = figure(tools=[PanTool(), WheelZoomTool(),
		BoxZoomTool(match_aspect=True), ResetTool()])
	p_tr = figure(tools=[PanTool(), WheelZoomTool(),
		BoxZoomTool(match_aspect=True), ResetTool()])
	p_ml = figure(tools=[PanTool(), WheelZoomTool(),
		BoxZoomTool(match_aspect=True), ResetTool()])
	p_mc = figure(tools=[PanTool(), WheelZoomTool(),
		BoxZoomTool(match_aspect=True), ResetTool()])
	p_mr = figure(tools=[PanTool(), WheelZoomTool(),
		BoxZoomTool(match_aspect=True), ResetTool()])
	p_bl = figure(tools=[PanTool(), WheelZoomTool(),
		BoxZoomTool(match_aspect=True), ResetTool()])
	p_bc = figure(tools=[PanTool(), WheelZoomTool(),
		BoxZoomTool(match_aspect=True), ResetTool()])
	p_br = figure(tools=[PanTool(), WheelZoomTool(),
		BoxZoomTool(match_aspect=True), ResetTool()])
	plots = [p_tl, p_tc, p_tr, p_ml, p_mc, p_mr, p_bl, p_bc, p_br]

	# Loop through and set plot parameters and add glyphs
	for i in range(0, len(spot_positions)):
		plots[i].plot_height = round(300)
		plots[i].plot_width = round(300)
		plots[i].x_range.start = spot_parameters[i].x_range_start
		plots[i].x_range.end = spot_parameters[i].x_range_end
		plots[i].y_range.start = spot_parameters[i].y_range_start
		plots[i].y_range.end = spot_parameters[i].y_range_end
		plots[i].image(image='image', source=src_image, x=0, y=0, dw='dw1',
			dh='dh1', palette="Spectral11", level="image")

		# Add an 'expected position'
		plots[i].circle_x([spot_parameters[i].x_pos_exp],
			[spot_parameters[i].y_pos_exp], size=10, color='blue', alpha=0.5)
		# Add a 'measured position'
		plots[i].circle_x([spot_parameters[i].x_pos_meas],
			[spot_parameters[i].y_pos_meas], size=10, color='white', alpha=0.5)
		plots[i].add_layout(Arrow(end=OpenHead(size=10, line_color="blue",
			line_width=1.5), x_start=spot_parameters[i].x_pos_exp, y_start=spot_parameters[i].y_pos_exp,
			x_end=spot_parameters[i].x_pos_meas, y_end=spot_parameters[i].y_pos_meas))
		plots[i].add_layout(Label(x=565, y=762.5, text_color = 'white',
			text = 'x=' + str(spot_parameters[i].x_pos_meas-spot_parameters[i].x_pos_exp) +
			' y=' + str(spot_parameters[i].y_pos_meas-spot_parameters[i].y_pos_exp)))

		plots[i].line(source=src_prof_points, x='x', y='y', line_width=2,
			color='black')
		c1 = plots[i].circle(source=src_prof_points, x='x', y='y', color='black',
			fill_alpha=0.5, size=12)
		plots[i].add_tools(PointDrawTool(renderers=[c1], num_objects=2))



	#
	# p_tl.plot_height = round(300)
	# p_tl.plot_width = round(300)
	# p_tl.x_range.start = spot_tl.x_range_start
	# p_tl.x_range.end = spot_tl.x_range_end
	# p_tl.y_range.start = spot_tl.y_range_start
	# p_tl.y_range.end = spot_tl.y_range_end
	# p_tl.image(image=[dict_image['image'][0]], x=0, y=0, dw=dict_image['dw1'][0], dh=dict_image['dh1'][0], palette="Spectral11", level="image")
	# # Add an 'expected position'
	# p_tl.circle_x([spot_tl.x_pos_exp], [spot_tl.y_pos_exp], size=10,
	# 	color='blue', alpha=0.5)
	# p_tl.circle_x([spot_tl.x_pos_meas], [spot_tl.y_pos_meas], size=10,
	# 	color='white', alpha=0.5)
	# p_tl.add_layout(Arrow(end=OpenHead(size=10, line_color="blue",
	# 	line_width=1.5), x_start=spot_tl.x_pos_exp, y_start=spot_tl.y_pos_exp,
	# 	x_end=spot_tl.x_pos_meas, y_end=spot_tl.y_pos_meas))
	# p_tl.add_layout(Label(x=565, y=762.5, text_color = 'white',
	# 	text = 'x=' + str(spot_tl.x_pos_meas-spot_tl.x_pos_exp) +
	# 	' y=' + str(spot_tl.y_pos_meas-spot_tl.y_pos_exp)))



	# # Thisis still a basic one
	# p3 = figure(tooltips=[("x", "$x"), ("y", "$y"), ("value", "@image")])
	# p3.plot_height = round(300)
	# p3.plot_width = round(300)
	# p3.x_range.start, p3.x_range.end = 700, 900
	# p3.y_range.start, p3.y_range.end = 500, 700
	# # p1.xaxis.axis_label = list[3]
	# # p1.yaxis.axis_label = list[4]
	# p3.image(image=[dict_image['image'][0]], x=0, y=0, dw=dict_image['dw1'][0], dh=dict_image['dh1'][0], palette="Spectral11", level="image")


	row1 = row(p_tl, p_tc, p_tr)
	row2 = row(p_ml, p_mc, p_mr)
	row3 = row(p_bl, p_bc, p_br)
	column1 = column(row1, row2, row3)
	column2 = column(row(p_prof, p_charmander), datatable_prof_points, p_main)
	layout = row(column1, column2)



	# Can probably make this much quicker by making seperate callbacks for each
	# individual image. It will be a lot of code but that way it doesn't have to
	# do a full loop to check if any others have changed.
	#
	# Might be that actually it's the rewritting of the display which is the
	# rate determining step. So by keeping the loop to just rewriting the
	# dictionary this might keep it quick enough?
	def callback_range(attr, old, new):

		for i in range(0, len(spot_positions)):
			spot_dict['x_'+spot_positions[i]] = [plots[i].x_range.start,
				plots[i].x_range.end, plots[i].x_range.end,
				plots[i].x_range.start, plots[i].x_range.start]
			spot_dict['y_'+spot_positions[i]] = [plots[i].y_range.start,
				plots[i].y_range.start, plots[i].y_range.end,
				plots[i].y_range.end, plots[i].y_range.start]

		df_spot = pd.DataFrame(spot_dict)
		src_spot.data = df_spot.to_dict(orient='list')

		return

	for i in range(0, len(spot_positions)):
		plots[i].x_range.on_change('start', callback_range)
		plots[i].x_range.on_change('end', callback_range)
		plots[i].y_range.on_change('start', callback_range)
		plots[i].y_range.on_change('end', callback_range)


	def callback_prof (attr, old, new):

		# I think src_prof.data already is a dictionary but just to make sure
		dict_prof_points = src_prof_points.data
		print(dict_prof_points)

		x_prof_start, x_prof_end = dict_prof_points['x']
		y_prof_start, y_prof_end = dict_prof_points['y']
		x_prof_start = float(x_prof_start)
		x_prof_end = float(x_prof_end)
		y_prof_start = float(y_prof_start)
		y_prof_end = float(y_prof_end)

		# Calculate how long the line is
		prof_length = math.sqrt((x_prof_start-x_prof_end)**2
			+ (y_prof_start-y_prof_end)**2)
		# Going to sample every 0.1 pixels which should be plenty
		prof_sample = int(prof_length/0.1)
		# Create a list of the x and y coordinates
		x_prof_sample = np.linspace(x_prof_start, x_prof_end, prof_sample)
		y_prof_sample = np.linspace(y_prof_start, y_prof_end, prof_sample)
		# Map coordinates is like an interpolation thing. Come back to this later?
		z_prof_sample = map_coordinates(arr1, np.vstack((y_prof_sample, x_prof_sample)))
		# Normalise to the max value in the profile
		z_prof_sample = z_prof_sample*(100/(max(z_prof_sample)))
		# Make it into a dictionary
		dict_prof = {'x': list(range(0, len(z_prof_sample))),
						'y': z_prof_sample}
		df_prof = pd.DataFrame(dict_prof)

		src_prof.data = df_prof.to_dict(orient='list')

		return

	src_prof_points.on_change('data', callback_prof)
	datatable_prof_points.on_change('source', callback_prof)



	# Return the panel

	return Panel(child = layout, title = 'ColorMapper')















#
