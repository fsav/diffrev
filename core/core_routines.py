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

import os, sys, copy, operator, time, datetime

if __name__ == '__main__':
    # otw when running tests we can't import other modules
    this_files_path = os.path.split(os.path.abspath(__file__))[0]
    sys.path.append(os.path.join(this_files_path,".."))

from storage import Storage, Revision, get_formatted_date, get_formatted_datetime
from note_listing import get_new_document_paths

from generation.static_html_generator import StaticHtmlGenerator
from diffing.diff_runner import DiffRunner
from server import localserver

def add_to_ignore_list(arguments, config):
    if arguments:
        print "For the moment, you can only ignore (or add) all new documents"
        print "(the argument list won't work)"
        print "Not doing anything. Exiting."
        return

    storage = Storage(config)
    
    new_files = get_new_document_paths(config, storage)

    storage.add_docs_to_ignored_list(new_files)

    for d in new_files:
        print "Now ignoring changes to", d

    if len(new_files) == 0:
        print "(No new files to ignore)"

def add_to_watched_list(arguments, config):
    if arguments:
        print "For the moment, you can only add (or ignore) all new documents"
        print "(the argument list won't work)"
        print "Not doing anything. Exiting."
        return

    storage = Storage(config)
    
    new_files = get_new_document_paths(config, storage)

    storage.add_docs_to_watched_list(new_files)

    for d in new_files:
        print "Now tracking", d

    if len(new_files) == 0:
        print "(No new files to add)"

def show_new_files(config):
    storage = Storage(config)
    
    new_files = get_new_document_paths(config, storage)

    print "List of new files:"

    for f in new_files:
        print f

    if len(new_files) == 0:
        print "(No new files)"

def generate_for_today(arguments, config):
    storage = Storage(config)

    invalid = False
    if len(arguments) not in (0,1):
        invalid = True

    days_in_advance = 0
    if len(arguments) == 1:
        try:
            days_in_advance = int(arguments[0])
        except:
            invalid = True

    if invalid:
        print "Sole argument accepted by 'today' is a number of days"
        print "for advance review."
        return

    the_date = datetime.date.today() + datetime.timedelta(days=days_in_advance)
    rev_objs = Revision.get_all_revisions_scheduled_before(storage, the_date)

    if len(rev_objs) == 0:
        print "No revisions for today, so not generating anything."
        print "(If you want to review in advance, add a number of days as"
        print " after 'diffrevision.py today', e.g. 'diffrevision.py t 2'"
        return

    generator = StaticHtmlGenerator(storage.config, storage)
    generator.generate_pages_and_index_for_revisions(rev_objs)

    print "When you're done, you must manually call " 
    print "    'diffrevision.py finished [list of revision numbers]'"
    print "and delete the temporary directory."

    if getattr(storage.config, 'use_local_server', False):
        print "STARTING LOCAL SERVER on port", localserver.SERVER_PORT
        localserver.LocalReviewServer.set_global_storage(storage)
        server = localserver.HTTPServer(('localhost', localserver.SERVER_PORT), localserver.LocalReviewServer)
        print 'Use <Ctrl-C> to stop'
        server.serve_forever()

def perform_diff(config, scheduler_getter):
    diffrunner = DiffRunner(config, scheduler_getter=config.get_scheduler)

    diffrunner.scan_files_for_changes()

def reviews_finished(arguments, config):
    storage = Storage(config)
    
    for revid_str in arguments:
        revid = int(revid_str)

        rev_obj = Revision.get_revision_from_id(storage, revid)

        rev_obj.num_revisions_done += 1

        new_date = config.get_scheduler(rev_obj.document_relative_path)\
                    .get_next_date(\
                        revision_object=rev_obj,
                        from_date=datetime.date.today())

        rev_obj.update_scheduled_date(new_date, update_num_revisions=True)

        print "Revision for", rev_obj.document_relative_path, \
            "(", get_formatted_datetime(rev_obj.datetime_diffed_on), ")",\
            "scheduled for ", get_formatted_date(new_date)

def list_all(config):
    storage = Storage(config)

    print "Printing all revisions in DB"

    Revision.print_all_revisions(storage)

#############
# tests

def test__reviews_finished__basic():
    import tempfile, shutil
    from core.storage import setup_temp_db, write_test_file, teardown_temp_db
    from diffing.diff_runner import DiffRunner
    import scheduling.fixed_scheduler

    notes_dir = tempfile.mkdtemp()
    store = setup_temp_db()

    store.config.notes_directory = notes_dir

    content_at_first = "First\nsecond"
    content_for_diff = content_at_first + "\nThird"

    write_test_file(os.path.join(notes_dir, "notes1.txt"), content_at_first)

    store.add_docs_to_watched_list(["notes1.txt"])
    
    diffrunner = DiffRunner(store.config, scheduler_getter=store.config.get_scheduler)
    # this should create the first revision
    diffrunner.scan_files_for_changes()

    rev_objs = store.get_revisions_for_document_path_sorted("notes1.txt")

    # HERE: reschedule based on id
    # note that mock config has a FixedScheduler with default intervals,
    # so next review should be in 6 days
    delta = datetime.timedelta(scheduling.fixed_scheduler.DEFAULT_INTERVALS[1])
    reviews_finished([str(rev_objs[0].id)], store.config)

    rev_objs2 = store.get_revisions_for_document_path_sorted("notes1.txt")

    assert rev_objs2[0].scheduled_date == datetime.date.today() + delta

    shutil.rmtree(notes_dir)
    teardown_temp_db(store)

if __name__ == '__main__':
    test__reviews_finished__basic()

