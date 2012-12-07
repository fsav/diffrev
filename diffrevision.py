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

import os, sys, copy, operator, time

# ease imports for imported modules
# (they need to access other modules in their parent directory)
this_files_path = os.path.split(os.path.abspath(__file__))[0]
sys.path.append(this_files_path)

from core import core_routines
from core import configuration as config

def usage():
    print """
diffrevision.py - A tool to review differences in text notes,
    with spaced-repetition inspired intervals.

Important: this a barebones implementation, a lot is to be done, or left
    as an exercise to the user (well, if the user is a Python programmer :-/ ).

To configure the path to your text files (among other things), please edit
core/configuration.py (TODO: make something cleaner for configuration...).

Commands are:

    diffrevision.py n (or show_new)
        Will list new files which are not yet being tracked for differences.

    diffrevision.py a (or add)
        Will add all new files to tracking. NOTE: this DOES NOT add a revision
        yet, you have to run the 'diff' command afterwards to create the first
        revisions for those new files.

    diffrevision.py i (or ignore)
        Will ignore all new files, so no reviews will be generated for those
        files.

    diffrevision.py t (or today)
        Will generate a (temporary) directory containing revisions to do
        today, and print the path to an index file (HTML page), which you can
        then load in your browser.

        You may also copy those files elsewhere to review, say on a mobile
        device.

        The index page will also contain a list of indices, which you can use
        when you're done to specify a review should be rescheduled (with the
        'finish' command). Try the checkboxes on the page, you'll get the idea.

        The temporary directory must be deleted manually for the moment.

    diffrevision.py d (or diff)
        Will check for changes in pages under tracking, and will add changes
        as reviews in the database. For file newly added to tracking, the
        whole content will be considered as 'to review' (highlighted).

    diffrevision.py f (or finish) [list of revision numbers]
        Will reschedule those revisions for review at some next date, counting
        from today.

        e.g. diffrevision.py f 2983 3829 3892
        This would reschedule those 3 reviews, taking into account the number
        of time they've been reviewed to determine next date.
    
"""

def parse_command():
    args = sys.argv[1:]

    if len(args) == 0 or args[0] in ('h','help','--help'):
        usage()
        return

    command = args[0]

    # TODO: syntax for changing config location
    # would come before the command
    # diffrevision.py --config ~/otherconfig today

    if command in ('n','show_new'):
        core_routines.show_new_files(config=config)
    elif command in ('a','add'):
        core_routines.add_to_watched_list(args[1:], config=config)
    elif command in ('i','ignore'):
        core_routines.add_to_ignore_list(args[1:], config=config)
    elif command in ('t','today'):
        core_routines.generate_for_today(args[1:], config=config)
    elif command in ('d','diff'):
        core_routines.perform_diff(config=config,
                            scheduler_getter=config.get_scheduler)
    elif command in ('f','finished'):
        core_routines.reviews_finished(args[1:], config=config)

    # debug and author-specific stuff
    elif command == 'list_all_revisions':
        core_routines.list_all(config=config)
    elif command == 'convert_old_text_file_database':
        core_routines.convert_old_text_file_database(config=config)

    else:
        print "Command not recognized:", command
        print "(type 'diffrevision.py help' for help)"

if __name__ == '__main__':
    parse_command()

