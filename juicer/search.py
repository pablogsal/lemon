#! /usr/bin/env python
# encoding:UTF-8

# Copyright (c) 2012 Victor Terron. All rights reserved.
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

import gtk

# LEMON modules
import glade
import mining
import util

class AmplitudesSearchPage(object):
    """ Encapsulates a gtk.GtkTreeView (and the corresponding tree store)
    with the results for the search of stars whose light curve amplitudes
    are correlated with the wavelength. Use the 'get_window' method to
    access a gtk.ScrolledWindow, with the tree view, meant to be used
    in the main gtk.GtkNotebook of the LEMONJuicerGUI class.

    """

    def __init__(self, builder, pfilters, include_ratios):
        """ Instantiation method for the AmplitudesSearchPage class.

        The 'builder' parameter must be the gtk.GtkBuilder of the parent GTK
        widget, while 'pfilters' is a sequence with the passband.Passband
        instances of the photometric filters of the amplitudes that will be
        added later with the 'add' method. If 'include_ratios' is True,
        additional columns will be created to store the ratio between each
        amplitude and its comparison standard deviation.

        """

        self.builder = builder
        self.builder.add_from_file(glade.AMPLITUDES_RESULTS)
        self.pfilters = pfilters
        self.include_ratios = include_ratios

        # ID, amplitudes and (optionally) Δ:stdev ratios
        args = [int] + [float] * len(pfilters)
        if include_ratios:
            args += [float] * len(pfilters)
        self.store = gtk.ListStore(*args)

        attrs = ['ID']
        attrs += ["Δ %s" % p.letter for p in pfilters]
        if include_ratios:
            attrs += ["Ratio %s" % p.letter for p in pfilters]

        self.view = self.builder.get_object('amplitudes-search-results')
        for index, title in enumerate(attrs):
            render = gtk.CellRendererText()
            column = gtk.TreeViewColumn(title, render, text = index)
            column.props.resizable = False
            column.set_sort_column_id(index)
            self.view.append_column(column)

    def add(self, star_id, amplitudes, ratios = None):
        """ Append a new row to the store.

        The 'star_id' must be an integer, the ID of the star, 'amplitudes' a
        sequence of floats with its amplitudes (in the same photometric filters
        and order that were passed to __init__), and 'ratios' a second sequence
        with the ratio between each amplitude and its comparison standard
        deviations. Note, however, that these ratios are ignored if
        'include_ratios' was not set to True at instantiation time.

        """

        row = [star_id] + list(amplitudes)
        if self.include_ratios:
            row += list(ratios)
        self.store.append(row)

    def get_window(self):
        """ Return a gtk.ScrolledWindow with the tree view of the stars """
        self.view.set_model(self.store)
        return self.builder.get_object('amplitudes-search-scrolled-window')

    def get_label(self):
        """ Return 'Amplitudes↑/↓', depending on the order of the filters """
        increasing = self.pfilters == sorted(self.pfilters)
        return 'Amplitudes' + ('↑' if increasing else '↓')


class AmplitudesSearchMessageWindow(object):

    DEFAULT_NUMBER_MIN_MAX_POINTS = 5
    DEFAULT_NUMBER_STDEVS = 10
    DEFAULT_AMPSTDEV_RATIO = 2

    def get(self, name):
        """ Access a widget in the interface """
        return self.builder.get_object(name)

    def __init__(self, parent_window, builder, db_path):

        self.builder = builder
        self.builder.add_from_file(glade.AMPLITUDES_DIALOG)
        self.miner = mining.LEMONdBMiner(db_path)

        self.dialog = self.get('amplitudes-search-dialog')
        self.dialog.set_resizable(False)
        self.dialog.set_title("Select stars by their amplitudes")
        self.dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        self.ok_button = self.dialog.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)

        # Set the labels of the radio buttons that select whether amplitudes
        # must increase or decrease to the photometric filters in the database
        pfilters = sorted(self.miner.pfilters)
        letters = [p.letter for p in pfilters]
        def make_label(x):
            return '-'.join(x)
        self.get('direct-correlation').set_label(make_label(letters))
        self.get('inverse-correlation').set_label(make_label(reversed(letters)))

        # Although the value of the adjustment is set in Glade, the spinbuttons
        # are all zero when the window is created, so we need to set them here
        namplitudes = self.get('amplitudes-how-many')
        nstdevs = self.get('comparison-stdevs-how-many')
        ratio = self.get('min-amplitude-stdev-ratio')
        namplitudes.set_value(self.DEFAULT_NUMBER_MIN_MAX_POINTS)
        nstdevs.set_value(self.DEFAULT_NUMBER_STDEVS)
        ratio.set_value(self.DEFAULT_AMPSTDEV_RATIO)

        self.dialog.set_transient_for(parent_window)
        self.dialog.set_position(gtk.WIN_POS_CENTER_ON_PARENT)

        # The checkbutton that controls whether stars with noisy amplitudes are
        # excluded from the search, and the widgets (spin and radio buttons)
        # that adjust the parameters used to detect these amplitudes.

        self.exclude_checkbox = self.get('filter-out-noisy')
        args = 'toggled', self.handle_toggle_exclude_noisy
        self.exclude_checkbox.connect(*args)

        w = {}
        w['nstdevs'] = self.get('comparison-stdevs-how-many')
        w['stdevs_mean'] = self.get('comparison-stdevs-mean')
        w['stdevs_median'] = self.get('comparison-stdevs-median')
        w['min_stdev_ratio'] = self.get('min-amplitude-stdev-ratio')
        self.exclude_widgets = w

        self.progressbar = self.get('search-progress-bar')

    def set_fraction(self, fraction):
        """ Fill in the portion of the bar specified by 'fraction'.

        The progress bar is only updated when the percentage varies; if, for
        example, it is 0.971 (97%), setting the fraction to 0.972 (still 97%)
        would only unnecessarily slow down the execution.

        """

        if fraction != self.progressbar.get_fraction():
            self.progressbar.set_fraction(fraction)
            # Ensure rendering is done immediately
            while gtk.events_pending():
                gtk.main_iteration()

    def run(self):
        """ Run the dialog window in a recursive loop.

        This method shows the dialog window and allows the user to adjust the
        parameters that will be used in the search. The search can be cancelled
        at any time by clicking 'Cancel', while clicking it when no search is
        in progress closes the window. The 'Ok' button is disabled to avoid
        running two searches in parallel.

        """

        def get_response(widget, response):
            self.response = response
        self.dialog.connect('response', get_response)

        while True:

            self.response = self.dialog.run()
            if self.response == gtk.RESPONSE_OK:

                increasing = self.get('direct-correlation').get_active()
                exclude_noisy = self.get('filter-out-noisy').get_active()

                args = (increasing,
                        int(self.get('amplitudes-how-many').get_value()),
                        self.get('amplitudes-median').get_active(),
                        exclude_noisy,
                        int(self.get('comparison-stdevs-how-many').get_value()),
                        self.get('comparison-stdevs-median').get_active(),
                        self.get('min-amplitude-stdev-ratio').get_value())

                g = self.miner.amplitudes_by_wavelength(*args)
                self.progressbar.set_text("Please wait...")
                self.ok_button.set_sensitive(False)

                # Photometric filters must be passed to AmplitudesSearchPage
                # in the same order in which the amplitudes will be added
                pfilters = sorted(self.miner.pfilters, reverse = not increasing)
                result = AmplitudesSearchPage(self.builder, pfilters, exclude_noisy)

                nstars = len(self.miner)
                for star_index, star_data in enumerate(g):

                    # Has the user pressed 'Cancel'?
                    if self.response == gtk.RESPONSE_CANCEL:
                        self.progressbar.set_fraction(0.0)
                        self.progressbar.set_text('')
                        self.ok_button.set_sensitive(True)
                        self.response = None
                        break

                    if star_data:
                        star_id = star_data[0]
                        _ , amplitudes, stdevs = zip(*star_data[-1])
                        if exclude_noisy:
                            ratios = [a / s for a, s in zip(amplitudes, stdevs)]
                        else:
                            ratios = None

                        result.add(star_id, amplitudes, ratios)

                    fraction = round(star_index / nstars, 2)
                    self.set_fraction(fraction)

                else:
                    self.dialog.destroy()
                    return result

            if self.response in [gtk.RESPONSE_CANCEL, gtk.RESPONSE_DELETE_EVENT]:
                self.dialog.destroy()
                break

    def handle_toggle_exclude_noisy(self, widget):
        """ Enable / disable widgets, as needed, when the 'Filter out those
        stars with one or more noisy amplitudes' check button is toggled """

        checkbox_enabled = widget.get_active()
        for w in self.exclude_widgets.itervalues():
            w.set_sensitive(checkbox_enabled)


def amplitudes_search(parent_window, builder, db):
    dialog = AmplitudesSearchMessageWindow(parent_window, builder, db)
    return dialog.run()
