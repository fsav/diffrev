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
import codecs

# otw when running tests we can't import other modules
# TODO: isolate tests and remove this
if __name__ == '__main__':
    this_files_path = os.path.split(os.path.abspath(__file__))[0]
    sys.path.append(os.path.join(this_files_path,".."))

import datetime
from core import storage
from core.storage import Revision
import plaintext_line_diff

class DiffRunner(object):
    def __init__(self, config, scheduler_getter,
                    get_changelist_fn=plaintext_line_diff.get_changelist,
                    store=None):
        if store is None:
            store = storage.Storage(config)

        self.config = config
        self.storage = store
        self.get_changelist_fn = get_changelist_fn
        self.scheduler_getter = scheduler_getter

    def scan_files_for_changes(self):
        watched = self.storage.get_all_watched_document_paths()

        if len(watched) == 0:
            print "No files under change tracking"
            return

        num_changes = 0

        print "Checking for changes in", len(watched), "files"
        progress_increment = len(watched) // 10
        progress_counter = 0

        for doc_idx, doc_relative_path in enumerate(watched):
            if self.check_for_changes_and_store_if_there_are(doc_relative_path):
                num_changes += 1
            if progress_increment != 0 and (doc_idx+1) % progress_increment == 0:
                progress_counter += 10
                print progress_counter, "% done"

        if num_changes == 0:
            print "(No reviewable changes found. Note that lines _deleted_"\
                    +" don't count as 'reviewable' changes.)"

    # returns True if there was a change
    def check_for_changes_and_store_if_there_are(self, doc_relative_path):
        revs = self.storage.\
                  get_revisions_for_document_path_sorted(\
                                        doc_relative_path,
                                        load_diff_content=False)

        # two paths here: either we already have at least one revision,
        # (in that case we just create more revisions) or not (in that case
        # we must create the first revision)

        if len(revs) > 0:
            lastrev = revs[-1]
            return self.check_for_changes_from_rev(lastrev)
        else:
            self.create_first_revision(doc_relative_path)
            return True

    # Should only be called if there's at least one revision stored already.
    def check_for_changes_from_rev(self, rev_obj):
        doc_absolute_path = os.path.join(self.config.notes_directory,
                                         rev_obj.document_relative_path)

        ###########
        # First check the doc still exists

        if not os.path.exists(doc_absolute_path):
            print "The file '" + doc_absolute_path + \
                "' was either deleted or moved, so changes cannot be "+\
                "tracked anymore."
            return

        ###########
        # Then check the modification date and avoid loading doc if it's
        # unchanged

        stat_struct = os.stat(doc_absolute_path)
        date_last_modified = datetime.datetime.fromtimestamp(\
                                                    stat_struct.st_mtime)

        epsilon = datetime.timedelta(seconds=2)

        if rev_obj.datetime_diffed_on + epsilon >= date_last_modified:
            return False

        ###########
        # Doc seems to have been modified, check diff

        # content was not loaded up to now
        rev_obj.load_diff_content()

        f = None
        try:
            f = codecs.open(doc_absolute_path, "r", self.config.notes_codec)
            current_integral_text = f.read()
        except IOError:
            if f is not None:
                f.close()
            print "IOError while reading file ", doc_absolute_path
            raise

        last_text = rev_obj.content

        changelist = self.get_changelist_fn(last_text, current_integral_text)

        # nothing new
        if not changelist:
            return False

        self.create_new_revision(rev_obj.document_relative_path,
                                current_integral_text, changelist)

        print "Revision was added for modified entry %s" \
                    % (rev_obj.document_relative_path,)

        return True

    def create_first_revision(self, doc_relative_path):
        doc_absolute_path = os.path.join(self.config.notes_directory,
                                         doc_relative_path)

        if not os.path.exists(doc_absolute_path):
            print "The _newly added_ file '" + doc_absolute_path + \
                "' was either deleted or moved, so changes won't be tracked."
            print "Re-create the document for changes to be tracked."
            return

        f = codecs.open(doc_absolute_path, "r", self.config.notes_codec)
        current_integral_text = f.read()
        f.close()

        # get the changelist considering the document's previous content was
        # the empty string ""
        changelist = self.get_changelist_fn("", current_integral_text)

        # we create a revision even though the document is empty

        self.create_new_revision(doc_relative_path,
                                current_integral_text, changelist)

        print "First revision was added for new entry %s" \
                    % (doc_relative_path,)

    def create_new_revision(self, document_relative_path,
                                    new_content, changelist):
        r = Revision(self.storage)

        r.document_relative_path = document_relative_path
        r.datetime_diffed_on = datetime.datetime.now()

        # just get the default first value, by passing no object to the scheduler
        # (and default is to use today() as start date)
        r.scheduled_date = self.scheduler_getter(r.document_relative_path).get_next_date(None)

        # no revisions done _for this diff_, not the document, by the way
        r.num_revisions_done = 0

        r.content = new_content
        r.changelist = changelist
        
        r.perform_insert()

##########################################
# tests

def test_create_first_then_diff():
    import tempfile, shutil
    from core.storage import setup_temp_db, write_test_file, teardown_temp_db
    from scheduling.fixed_scheduler import FixedScheduler

    notes_dir = tempfile.mkdtemp()
    store = setup_temp_db()

    store.config.notes_directory = notes_dir

    content_at_first = "First\nsecond"
    content_for_diff = content_at_first + "\nThird"

    write_test_file(os.path.join(notes_dir, "notes1.txt"), content_at_first)

    store.add_docs_to_watched_list(["notes1.txt"])
    
    diffrunner = DiffRunner(store.config, scheduler_getter=lambda x: FixedScheduler())
    # this should create the first revision
    diffrunner.scan_files_for_changes()

    # then check to see that file's path has a revision, containing all lines
    rev_objs = store.get_revisions_for_document_path_sorted("notes1.txt")

    assert len(rev_objs) == 1
    assert rev_objs[0].content == content_at_first
    assert rev_objs[0].changelist == "0\n1"

    # wait a bit otw we get a problem with collision of two revisions having
    # the same timestamp... if timestamp difference is less than 2 seconds, the
    # diff is not taken
    time.sleep(3)
    
    # then modify the file
    write_test_file(os.path.join(notes_dir, "notes1.txt"), content_for_diff)

    # create new revision
    diffrunner.scan_files_for_changes()

    # check for two revisions, second one only has third line modified 
    rev_objs = store.get_revisions_for_document_path_sorted("notes1.txt")

    assert len(rev_objs) == 2
    assert rev_objs[0].content == content_at_first
    assert rev_objs[0].changelist == "0\n1"
    assert rev_objs[1].content == content_for_diff
    assert rev_objs[1].changelist == "2"

    shutil.rmtree(notes_dir)
    teardown_temp_db(store)
 
if __name__ == '__main__':
    import tempfile, shutil
    test_create_first_then_diff()

