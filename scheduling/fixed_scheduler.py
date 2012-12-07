# This file is part of python-diffrevision
# Copyright (C) 2011 Francois Savard 
#
# python-diffrevision is free software:
# you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# python-diffrevision is distributed in the hope that
# it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with python-diffrevision (see license.txt)
# If not, see <http://www.gnu.org/licenses/>.

from datetime import date, datetime, timedelta
import random

DEFAULT_INTERVALS = [2,6,14,30,45,90,120,180,360,720,99999]

class FixedScheduler(object):
    def __init__(self, intervals=DEFAULT_INTERVALS, random_plusminus=None):
        self.intervals = intervals

        if random_plusminus is None:
            self.random_plusminus = [0 for i in intervals]
        else:
            self.random_plusminus = random_plusminus

        assert len(self.random_plusminus) == len(self.intervals)

    def get_next_date(self, revision_object=None, from_date=None):
        if revision_object is not None:
            num_revisions = revision_object.num_revisions_done
        else:
            # if called without a revision object, means we haven't
            # done any revision yet... but even if the object is passed
            # it's still possible to get len(past_dates) to be 0, so two
            # code paths lead to this result
            num_revisions = 0

        if from_date is None:
            from_date = date.today()

        # these lists must have same length, otw it probably means there's
        # an error in the intentions behind the parameters
        assert len(self.random_plusminus) == len(self.intervals)

        if num_revisions >= len(self.intervals):
            num_revisions = len(self.intervals)-1

        plusminus = random.randint(-self.random_plusminus[num_revisions],
                        self.random_plusminus[num_revisions])

        next_date = from_date + \
                timedelta(days=self.intervals[num_revisions]) + \
                timedelta(days=plusminus)

        assert type(next_date) == date

        return next_date

