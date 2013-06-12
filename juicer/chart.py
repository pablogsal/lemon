#! /usr/bin/env python

# Copyright (c) 2013 Victor Terron. All rights reserved.
# Institute of Astrophysics of Andalusia, IAA-CSIC
#
# This file is part of LEMON.
#
# LEMON is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import division

import aplpy
import gtk
import os
import pyfits

import matplotlib.figure
from matplotlib.backends.backend_gtkagg \
     import FigureCanvasGTKAgg as FigureCanvas
from matplotlib.backends.backend_gtkagg \
     import NavigationToolbar2GTKAgg as NavigationToolbar

# LEMON modules
import glade

class FindingChartDialog(object):
    """ GTK.Dialog that displays the reference frame """

    # Width of the window, in pixels
    WIDTH = 650

    def __init__(self, parent_window, builder, db):

        self.builder = builder
        self.builder.add_from_file(glade.FINDING_CHART_DIALOG)
        self.dialog = self.builder.get_object('finding-chart-dialog')
        self.dialog.set_resizable(True)
        self.dialog.set_title("Finding Chart: %s" % db.field_name)
        self.dialog.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
        self.dialog.set_default_response(gtk.RESPONSE_CLOSE)

        # The matplotlib figure...
        matplotlib_container = self.builder.get_object('matplotlib-container')
        self.image_box = self.builder.get_object('image-container-box')
        self.figure = matplotlib.figure.Figure()
        canvas = FigureCanvas(self.figure)
        self.image_box.pack_start(canvas)

        # ... and the navigation toolbar
        self.navigation_box = self.builder.get_object('navigation-toolbar-box')
        navig = NavigationToolbar(canvas, self.image_box)
        self.navigation_box.pack_start(navig)
        matplotlib_container.show_all()

        self.dialog.set_transient_for(parent_window)
        self.dialog.set_position(gtk.WIN_POS_CENTER_ON_PARENT)

        ax1 = self.figure.add_subplot(111)
        ax1.get_xaxis().set_visible(False)
        ax1.get_yaxis().set_visible(False)

        # Temporarily save to disk the FITS file used as a reference frame
        path = db.mosaic

        try:
            with pyfits.open(path) as hdu:
                data = hdu[0].data
        finally:
            os.unlink(path)

        self.aplpy_plot = aplpy.FITSFigure(data, figure = self.figure)
        self.aplpy_plot.show_grayscale()

        # The dialog has always the same width; the height is adjusted
        # proportionally depending on the dimensions of the FITS image.
        size = data.shape[::-1]
        size_ratio = size[1] / size[0]
        new_size = self.WIDTH, int(self.WIDTH * size_ratio)
        self.dialog.resize(*new_size)

    def run(self):
        try:
            self.dialog.run()
        finally:
            self.dialog.destroy()
