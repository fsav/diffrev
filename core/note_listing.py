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

import os, sys

# all entries, ie. all files that match the extension criterion
def get_unfiltered_document_paths(config):
    recognized_files = []
    all_files = os.listdir(config.notes_directory)
    for f in all_files:
        for ext in config.recognized_extensions:
            if f.endswith(ext):
                recognized_files.append(f)
    return recognized_files

def list_minus_list(minuend, subtrahend):
    ret = []
    for el in minuend:
        if not el in subtrahend:
            ret.append(el)
    return ret

def filter_ignore_patterns(filepaths, config):
    retval = []
    for path in filepaths:
        e = os.path.split(path)[1]
        ok = True
        for pattern in config.ignored_filename_patterns:
            if pattern.match(e):
                ok=False
        if ok:
            retval.append(e)
    return retval

def get_new_document_paths(config, storage):
    unfiltered_files = get_unfiltered_document_paths(config)
    watched_files = storage.get_all_watched_document_paths()
    ignored_files = storage.get_ignored_document_relative_paths()

    new_files = list_minus_list(unfiltered_files, watched_files)
    new_files = list_minus_list(new_files, ignored_files)
    new_files = filter_ignore_patterns(new_files, config)

    return new_files


####################
# tests

def test_get_new_files():
    from storage import \
            setup_temp_wiki_and_corresponding_rev_for_test_ignored_watched_new
    
    notes_dir, store = \
        setup_temp_wiki_and_corresponding_rev_for_test_ignored_watched_new()

    store.config.ignored_filename_patterns.append(re.compile("ignored.*"))

    new_files = get_new_document_paths(store.config, store)

    assert set(new_files) == set(['notes_new.txt','notes_new2.txt'])

    shutil.rmtree(notes_dir)
    teardown_temp_db(store)
    
if __name__ == '__main__':
    # otw when running tests we can't import other modules
    this_files_path = os.path.split(os.path.abspath(__file__))[0]
    sys.path.append(os.path.join(this_files_path,".."))

    import tempfile
    import shutil
    import re
    from storage import teardown_temp_db

    test_get_new_files()
