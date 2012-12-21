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

import os,sys,copy,operator,time
import datetime
import sqlite3
import codecs

DB_FILENAME = 'db.sqlite3'
IGNORED_LIST = 'ignored_entries.dat'
REVISIONS_CONTENT_DIRNAME = 'revisions'
IGNORED_LIST_FILENAME = 'ignored.txt'

REVISION_CONTENT_FILENAME = 'content.txt'
CHANGELIST_FILENAME = 'changelist.txt'

TIMESTAMP_FORMAT = "%Y-%m-%d-%H-%M-%S"
DATE_FORMAT = "%Y-%m-%d"

REVISIONS_TABLE_NAME = 'revisions'
CREATE_TABLE_STATEMENT = "create table "+REVISIONS_TABLE_NAME+"("+\
                            "id INTEGER PRIMARY KEY,"+\
                            "document_relative_path varchar(256),"+\
                            "datetime_diffed_on timestamp,"+\
                            "scheduled_date date,"+\
                            "num_revisions_done integer,"+\
                            "hidden integer not null default 0)"
ALL_COL_NAMES = "id, document_relative_path, datetime_diffed_on,"+\
                    " scheduled_date, num_revisions_done, hidden"

def get_formatted_date(date):
    as_datetime = datetime.datetime(year=date.year,
                                month=date.month,
                                day=date.day)
    return as_datetime.strftime(DATE_FORMAT)

def get_formatted_datetime(dt):
    return dt.strftime(TIMESTAMP_FORMAT)

class Storage(object):
    def __init__(self, config):
        self.config = config

        self.revisions_content_abspath = \
            os.path.join(self.config.diffrevision_base_directory,
                            REVISIONS_CONTENT_DIRNAME)

        self.ignored_list_file_abspath = \
                os.path.join(self.config.diffrevision_base_directory,
                                   IGNORED_LIST_FILENAME)

        self.create_basic_files_if_necessary()

        self.db_connection = None
        self.db_cursor = None

        self.connect_to_db_or_create()

    def create_basic_files_if_necessary(self):
        if not os.path.exists(self.revisions_content_abspath):
            os.mkdir(self.revisions_content_abspath)

        if not os.path.exists(self.ignored_list_file_abspath):
            # TODO: codec
            f = open(self.ignored_list_file_abspath,"w")
            f.write("")
            f.close()

        assert os.path.isdir(self.revisions_content_abspath)

    def create_tables(self):
        self.db_cursor.execute(CREATE_TABLE_STATEMENT)
        
    def connect_to_db_or_create(self):
        db_path = os.path.join(self.config.diffrevision_base_directory,
                                DB_FILENAME)

        didnt_exist = False
        if not os.path.exists(db_path):
            didnt_exist = True

        # the detect_types option makes sure timestamp and date columns
        # are converted correclty in the Python layer
        self.db_connection = sqlite3.connect(db_path,
                detect_types=sqlite3.PARSE_DECLTYPES)
        self.db_cursor = self.db_connection.cursor()

        if didnt_exist:
            self.create_tables()

    def close_connection(self):
        self.db_connection.close()

    def get_revisions_for_document_path_sorted(self, doc_relative_path,
                                               load_diff_content=True):
        # we could also get the revisions from looking at the directory
        # containing them, but then we'd have to fetch them in the db
        # afeterwards anyway

        self.db_cursor.execute("SELECT "+ALL_COL_NAMES+\
                                    " FROM "+REVISIONS_TABLE_NAME+\
                                    " WHERE document_relative_path=? "+\
                                    " ORDER BY datetime_diffed_on ASC;",
                                    (doc_relative_path,))

        # it's quite possible that there is no result, by the way, as when
        # checking if an entry has any revision at all when it's just been 
        # added
        results = []
        rows = self.db_cursor.fetchall()
        for row in rows:
            results.append(\
                Revision.create_from_record(self, row,\
                                    load_diff_content=load_diff_content))
        return results

    def get_all_watched_document_paths(self):
        # watched documents are simply the ones which have a directory
        return os.listdir(self.revisions_content_abspath)

    def get_ignored_document_relative_paths(self):
        f = open(self.ignored_list_file_abspath, "r")
        entries = f.readlines()
        entries = [l.rstrip() for l in entries]
        f.close()

        return entries

    def add_docs_to_watched_list(self, docs_relative_paths):
        # TODO: make this be able to handle subdirectories
        for rel_path in docs_relative_paths:
            complete_path = os.path.join(\
                                self.revisions_content_abspath, rel_path)

            # TODO: handle errors, at least "dir already exists"
            os.mkdir(complete_path)

    def add_docs_to_ignored_list(self, docs_relative_paths):
        f = open(self.ignored_list_file_abspath, "a")
        for rel_path in docs_relative_paths:
            print >>f, rel_path
        f.close()

class Revision(object):
    def __init__(self, storage):
        self.storage = storage

        self.id = None
        self.document_relative_path = None
        self.datetime_diffed_on = None
        self.scheduled_date = None
        self.num_revisions_done = None
        self.hidden = None

        self.content = None
        self.changelist = None

    def __str__(self):
        return ("{Revision object, "+\
            "id=%s, "+\
            "document_relative_path=%s, "+\
            "datetime_diffed_on=%s, "+\
            "scheduled_date=%s, "+\
            "num_revisions_done=%s, "+\
            "hidden=%s, "+\
            "content len=%s, "+\
            "changelist len=%s}") % (\
                    self.id,
                    self.document_relative_path,
                    self.datetime_diffed_on,
                    self.scheduled_date,
                    self.num_revisions_done,
                    self.hidden,
                    None if self.content is None else len(self.content),
                    None if self.changelist is None else len(self.changelist))

    def perform_insert(self, no_content=False):
        self.storage.db_cursor.execute(\
            'INSERT INTO '+REVISIONS_TABLE_NAME\
                 +' (' + ALL_COL_NAMES + ') '\
                 +'VALUES (null, ?, ?, ?, ?, ?)', # null is for ID
                    (self.document_relative_path,\
                     self.datetime_diffed_on,\
                     self.scheduled_date,\
                     self.num_revisions_done,\
                     False)) # hidden = False, at first

        # set id from autoassigned value
        # rowid is the same as primary key for sqlite
        # http://www.sqlite.org/c3ref/last_insert_rowid.html
        self.id = self.storage.db_cursor.lastrowid

        if not no_content:
            self.create_revision_directory()

            self.save_content()
            self.save_changelist()

        self.storage.db_connection.commit()

    def update_scheduled_date(self, scheduled_for, update_num_revisions=False):
        assert self.storage is not None
        assert self.id is not None

        if update_num_revisions:
            self.storage.db_cursor.execute(\
                'UPDATE '+REVISIONS_TABLE_NAME+\
                ' SET scheduled_date=?, num_revisions_done=?'+\
                ' WHERE id=?',
                    (scheduled_for,self.num_revisions_done,self.id))
        else:
            self.storage.db_cursor.execute(\
                'UPDATE '+REVISIONS_TABLE_NAME+' SET scheduled_date=? WHERE id=?',
                    (scheduled_for,self.id))

        self.storage.db_connection.commit()

    def set_hidden_state(self, hidden=True):
        assert self.storage is not None
        assert self.id is not None

        hidden_value = (1 if hidden else 0)

        self.storage.db_cursor.execute(\
                'UPDATE '+REVISIONS_TABLE_NAME+' SET hidden=? WHERE id=?',
                    (hidden_value,self.id))

        self.storage.db_connection.commit()

    @staticmethod
    def create_from_record(storage, record, load_diff_content=True):
        r = Revision(storage)

        r.id = record[0]
        r.document_relative_path = record[1]
        r.datetime_diffed_on = record[2]
        r.scheduled_date = record[3]
        r.num_revisions_done = record[4]
        r.hidden = (record[5] != 0)

        if load_diff_content:
            r.load_diff_content()

        return r

    def load_diff_content(self):
        #import pdb; pdb.set_trace()
        self.load_content()
        self.load_changelist()

    @staticmethod
    def get_revision_from_id(storage, id):
        storage.db_cursor.execute("SELECT "+ALL_COL_NAMES+\
                                    " FROM "+REVISIONS_TABLE_NAME+\
                                    " WHERE id=?;",
                                    (id,))

        results = []
        rows = storage.db_cursor.fetchall()
        for row in rows:
            results.append(Revision.create_from_record(storage, row))

        assert len(results) <= 1

        if results:
            return results[0]
        else:
            return None

    # a "print" rather than a "get", to print as we fetch... which might take
    # a long time with thousands of reviews
    # more for debugging purposes
    @staticmethod
    def print_all_revisions(storage):
        storage.db_cursor.execute("SELECT "+ALL_COL_NAMES+\
                                  " FROM "+REVISIONS_TABLE_NAME+";")

        results = []
        rows = storage.db_cursor.fetchall()
        for row in rows:
            print Revision.create_from_record(storage, row)
        return results

    @staticmethod
    def get_all_revisions_scheduled_before(storage, date=None):
        if date is None:
            date = datetime.date.today()

        storage.db_cursor.execute("SELECT "+ALL_COL_NAMES+\
                                    " FROM "+REVISIONS_TABLE_NAME+\
                                    " WHERE scheduled_date <= ?;",
                                    (date,))

        results = []
        rows = storage.db_cursor.fetchall()
        for row in rows:
            results.append(Revision.create_from_record(storage, row,
                                                       load_diff_content=True))
        return results

    def get_relative_path_plus_timestamp(self):
        if self.document_relative_path is None or self.datetime_diffed_on is None:
            raise RuntimeError()

        ts = self.datetime_diffed_on.strftime(TIMESTAMP_FORMAT)

        return os.path.join(self.document_relative_path, ts)

    def get_full_directory_path(self):
        return os.path.join(self.storage.revisions_content_abspath,
                                self.get_relative_path_plus_timestamp())

    def create_revision_directory(self):
        # first create the document directory
        doc_dir = os.path.join(self.storage.revisions_content_abspath,
                                self.document_relative_path)
        if not os.path.exists(doc_dir):
            # TODO: handle mkdir errors
            os.mkdir(doc_dir)

        os.mkdir(self.get_full_directory_path())

    def get_file_content(self, filename):
        file_path = os.path.join(self.get_full_directory_path(), filename)

        f = codecs.open(file_path, "r", self.storage.config.notes_codec)
        content = f.read()
        f.close()

        return content

    def set_file_content(self, filename, content):
        file_path = os.path.join(self.get_full_directory_path(), filename)

        f = codecs.open(file_path, "w", self.storage.config.notes_codec)
        f.write(content)
        f.close()

    def load_content(self, force=False):
        if self.content is None or force:
            self.content = self.get_file_content(REVISION_CONTENT_FILENAME)

    def save_content(self):
        assert self.content is not None
        self.set_file_content(REVISION_CONTENT_FILENAME, self.content)

    def load_changelist(self, force=False):
        if self.changelist is None or force:
            self.changelist = self.get_file_content(CHANGELIST_FILENAME)

    def save_changelist(self):
        assert self.changelist is not None
        self.set_file_content(CHANGELIST_FILENAME, self.changelist)

##############
# tests
# part of these test setup routines are reused for tests in note_listing

class mock_config(object):
    def __init__(self, directory):
        import scheduling.fixed_scheduler
        self.diffrevision_base_directory = directory
        self.ignored_filename_patterns = []
        self.notes_directory = ""
        self.recognized_extensions = [".txt"]
        self.scheduler = scheduling.fixed_scheduler.FixedScheduler()
        self.get_scheduler = lambda title: self.scheduler
        self.notes_codec = "utf-8"

def write_test_file(path, content):
    # this is for tests, in a temp directory, so no exception catching
    f = open(path,"w")
    f.write(content)
    f.close()

def setup_temp_db():
    import tempfile, shutil
    tmpdir = tempfile.mkdtemp()

    config = mock_config(tmpdir)

    # this should create the db
    store = Storage(config)

    return store

def teardown_temp_db(storage):
    import shutil
    storage.close_connection()
    shutil.rmtree(storage.config.diffrevision_base_directory)

def setup_temp_wiki_and_corresponding_rev_for_test_ignored_watched_new():
    import tempfile, shutil
    notes_dir = tempfile.mkdtemp()
    store = setup_temp_db()

    store.config.notes_directory = notes_dir

    write_test_file(os.path.join(notes_dir, "notes_ignored.txt"), "Ignore\nignore")
    write_test_file(os.path.join(notes_dir, "notes_ignored2.txt"), "Ignore\nignore")
    write_test_file(os.path.join(notes_dir, "notes_watched.txt"),
                                            "Watch\nwatch\nwatch")
    write_test_file(os.path.join(notes_dir, "notes_watched2.txt"),
                                            "Watch\nwatch\nwatch")
    write_test_file(os.path.join(notes_dir, "notes_new.txt"), "New\nnew\nnew")
    write_test_file(os.path.join(notes_dir, "notes_new2.txt"), "New\nnew\nnew")
    write_test_file(os.path.join(notes_dir, "ignoredfilename.txt"),
                                                "ignore patterns")

    store.add_docs_to_watched_list(["notes_watched.txt", "notes_watched2.txt"])

    store.add_docs_to_ignored_list(["notes_ignored.txt","notes_ignored2.txt"])
    
    return notes_dir, store

def test_ignored_watched_new():
    notes_dir, store = \
        setup_temp_wiki_and_corresponding_rev_for_test_ignored_watched_new()

    watched = store.get_all_watched_document_paths()
    ignored = store.get_ignored_document_relative_paths()

    assert set(watched) == set(['notes_watched.txt','notes_watched2.txt'])
    assert set(ignored) == set(['notes_ignored.txt','notes_ignored2.txt'])
    
    shutil.rmtree(notes_dir)
    teardown_temp_db(store)

def test_db_creation():
    store = setup_temp_db()

    db_path = os.path.join(store.config.diffrevision_base_directory,
                                DB_FILENAME)
    assert os.path.exists(db_path)

    teardown_temp_db(store)

def test_base_insert_select():
    storage = setup_temp_db()

    r = Revision(storage)

    r.document_relative_path = "mynotes.txt"
    r.datetime_diffed_on = datetime.datetime.now() - datetime.timedelta(days=2)
    r.scheduled_date = datetime.date.today()
    r.num_revisions_done = 4

    r.content = u"blah\nblah"
    r.changelist = u"0\n0\n1"
    
    r.perform_insert()

    storage.close_connection()

    # now try to reload

    mock_config = storage.config

    storage2 = Storage(mock_config)

    revs = Revision.get_all_revisions_scheduled_before(storage2)

    assert len(revs) == 1

    assert revs[0].id == r.id
    assert revs[0].document_relative_path == r.document_relative_path
    assert revs[0].datetime_diffed_on == r.datetime_diffed_on
    assert revs[0].scheduled_date == r.scheduled_date
    assert revs[0].num_revisions_done == r.num_revisions_done

    assert revs[0].content == r.content
    assert revs[0].changelist == r.changelist

    # another test while we're at it, for get_revision_from_id
    r_from_id = Revision.get_revision_from_id(storage2, r.id)

    assert r_from_id.id == r.id
    assert r_from_id.document_relative_path == r.document_relative_path
    assert r_from_id.datetime_diffed_on == r.datetime_diffed_on
    assert r_from_id.scheduled_date == r.scheduled_date
    assert r_from_id.num_revisions_done == r.num_revisions_done

    assert r_from_id.content == r.content
    assert r_from_id.changelist == r.changelist

    teardown_temp_db(storage)

def test_base_update_scheduled_date():
    storage = setup_temp_db()

    r = Revision(storage)

    r.document_relative_path = "mynotes.txt"
    r.datetime_diffed_on = datetime.datetime.now() - datetime.timedelta(days=2)
    r.scheduled_date = datetime.date.today()
    r.num_revisions_done = 4

    r.content = u"blah\nblah"
    r.changelist = u"0\n0\n1"
    
    r.perform_insert()

    # HERE: new date update
    new_date = datetime.date.today() + datetime.timedelta(days=8)
    r.update_scheduled_date(new_date)

    storage.close_connection()

    # now try to reload

    mock_config = storage.config

    storage2 = Storage(mock_config)

    future_date = datetime.date.today() + datetime.timedelta(days=15)
    revs = Revision.get_all_revisions_scheduled_before(storage2, future_date)

    assert revs[0].scheduled_date == new_date

    teardown_temp_db(storage)
    

def test_update_scheduled_date_and_update_num_revisions():
    storage = setup_temp_db()

    r = Revision(storage)

    r.document_relative_path = "mynotes.txt"
    r.datetime_diffed_on = datetime.datetime.now() - datetime.timedelta(days=2)
    r.scheduled_date = datetime.date.today()
    r.num_revisions_done = 4

    r.content = u"blah\nblah"
    r.changelist = u"0\n0\n1"
    
    r.perform_insert()

    new_date = datetime.date.today() + datetime.timedelta(days=8)
    # HERE: new date update PLUS INCREASE 
    r.num_revisions_done += 1
    r.update_scheduled_date(new_date, update_num_revisions=True)

    storage.close_connection()

    # now try to reload

    mock_config = storage.config

    storage2 = Storage(mock_config)

    future_date = datetime.date.today() + datetime.timedelta(days=15)
    revs = Revision.get_all_revisions_scheduled_before(storage2, future_date)

    assert revs[0].scheduled_date == new_date
    assert revs[0].num_revisions_done == 5

    teardown_temp_db(storage)
    

if __name__ == '__main__':

    # otw when running tests we can't import other modules
    this_files_path = os.path.split(os.path.abspath(__file__))[0]
    sys.path.append(os.path.join(this_files_path,".."))

    import tempfile, shutil
    test_db_creation()
    test_base_insert_select()
    test_base_update_scheduled_date()
    test_ignored_watched_new()
    test_update_scheduled_date_and_update_num_revisions()


