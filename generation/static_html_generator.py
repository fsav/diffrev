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

#################
# For an architecture overview of this module, see __init__.py
#################

import os, sys, copy, operator, time
import codecs

# otw when running tests we can't import other modules
# TODO: isolate tests and remove this
if __name__ == '__main__':
    this_files_path = os.path.split(os.path.abspath(__file__))[0]
    sys.path.append(os.path.join(this_files_path,".."))

from core import storage
from core.storage import get_formatted_datetime, get_formatted_date
import tempfile

import diffing.plaintext_line_diff

from server import localserver

REVISION_CONTENT_TEMPLATE_FILE = "revision_content.html"
REVISION_LIST_TEMPLATE_FILE = "revision_list.html"

REVISION_CONTENT_TEMPLATE = None
REVISION_LIST_TEMPLATE = None

def load_template(template_rel_path):
    python_files_path = os.path.split(os.path.abspath(__file__))[0]
    python_files_path = os.path.join(python_files_path,"..")

    template_abspath = os.path.join(python_files_path,
                            "templates", template_rel_path)
    f = open(template_abspath, "r")
    c = f.read()
    f.close()
    return c

def apply_revision_content_template(title, revision_content, server_based_code=""):
    global REVISION_CONTENT_TEMPLATE
    if REVISION_CONTENT_TEMPLATE is None:
        REVISION_CONTENT_TEMPLATE = \
                load_template(REVISION_CONTENT_TEMPLATE_FILE)
    return REVISION_CONTENT_TEMPLATE % locals()

def apply_revision_list_template(revisions_list_html, id_list, output_dir):
    global REVISION_LIST_TEMPLATE

    checkbox_list = ",".join(["'checkbox"+str(i)+"'" for i in id_list])
    revision_ids = ",".join([str(i) for i in id_list])

    if REVISION_LIST_TEMPLATE is None:
        REVISION_LIST_TEMPLATE = \
                load_template(REVISION_LIST_TEMPLATE_FILE)
    return REVISION_LIST_TEMPLATE % locals()

def generate_html_for_revision_list(list_of_title_id_date1_date2_link):
    the_htmls = []
    for title,revid,date_diff,date_for,link in list_of_title_id_date1_date2_link:
        li_html = """
                <li>
                    <input type="checkbox" id="checkbox%s"
                            onchange="update_list();"/>
                    [%s]
                    <a href="%s" onmouseup="$('checkbox%s').checked = true; update_list();">
                        %s (diffed on %s)
                    </a>
                    -- scheduled for %s
                </li>""" % (revid, revid, link, revid, title,\
                        get_formatted_datetime(date_diff),\
                        get_formatted_date(date_for))
                
        the_htmls.append(li_html)
    return "\n".join(the_htmls)

class BasicLineBasedHtmlFormatter():
    def format(self, rev_obj):
        orig_lines = rev_obj.content.splitlines()

        str_line_nos = rev_obj.changelist.splitlines()
        line_nos_with_changes = [int(lineno) for lineno in str_line_nos]

        new_lines = []
        for lineno, line in enumerate(orig_lines):
            if lineno in line_nos_with_changes:
                new_lines.append("<span class='hl'>"+line+"</span>")
            else:
                new_lines.append(line)

        return "<br/>".join(new_lines)

class StaticHtmlGenerator(object):
    def __init__(self, config,
                 store=None):
        if not store:
            store = Storage(config)

        self.storage = store
        self.config = config

        if self.config.wiki_syntax == 'wikidpad':
            import wikidpad_formatter
            self.formatter = wikidpad_formatter.WikidpadFormatter(config)
        else:
            self.formatter = BasicLineBasedHtmlFormatter()

    def generate_pages_and_index_for_revisions(self, revision_objects):
        output_dir = tempfile.mkdtemp(dir=self.config.tmp_directory)

        index_html = []
        li_list = []
        id_list = []

        for rev_obj in revision_objects:
            if rev_obj.hidden:
                continue

            lines = rev_obj.content.splitlines()
            spans_per_line = [[] for l in lines]

            # TODO: escape string 
            title = rev_obj.document_relative_path
            link = title + "__" + \
                get_formatted_datetime(rev_obj.datetime_diffed_on) + ".html"
            scheduled_date = get_formatted_date(rev_obj.scheduled_date)

            id_list.append(rev_obj.id)

            # that's not very pretty, so TODO just pass rev_obj...
            li_list.append((title,\
                    rev_obj.id,
                    rev_obj.datetime_diffed_on,\
                    rev_obj.scheduled_date,\
                    link))
            
            html = self.formatter.format(rev_obj)

            server_based_code = ''
            if getattr(self.config, 'use_local_server', False):
                server_based_code = """
                        <!--<script type="text/javascript" src="/js/jQuery.min.js"></script>-->
                        <a href="http://localhost:%s/hidereview/?reviewid=%s">Don't show this review again</a>
                        <script type="text/javascript">

                        window.deleteEntry = function() {
                                document.location.href = 'http://localhost:%s/hidereview/?reviewid=%s';
                        }

                        </script>
                        """ % (localserver.SERVER_PORT, rev_obj.id, localserver.SERVER_PORT, rev_obj.id)

            html = apply_revision_content_template(title, html, server_based_code)

            # TODO: error handling
            f = codecs.open(os.path.join(output_dir, link), "w", "utf-8")
            f.write(html)
            f.close()

        index_path = os.path.join(output_dir, "index.html")
        f = open(index_path, "w")
        f.write(apply_revision_list_template(\
                    generate_html_for_revision_list(\
                                li_list),
                    id_list, output_dir))
        f.close()

        print "Finished generation. Index at", index_path
        
        return output_dir


######################
# tests

def setup_revisions_notes1():
    import tempfile, shutil
    from core.storage import setup_temp_db, write_test_file, teardown_temp_db
    from diffing.diff_runner import DiffRunner

    notes_dir = tempfile.mkdtemp()
    store = setup_temp_db()

    store.config.notes_directory = notes_dir

    content_at_first = "First\nsecond"
    content_for_diff = content_at_first + "\nThird"

    write_test_file(os.path.join(notes_dir, "notes1.txt"), content_at_first)

    # mark the file as watched for changes
    store.add_docs_to_watched_list(["notes1.txt"])
    
    diffrunner = DiffRunner(store.config)

    # this should create the first revision
    diffrunner.scan_files_for_changes()
    
    # then modify the file
    write_test_file(os.path.join(notes_dir, "notes1.txt"), content_for_diff)

    # wait a bit otw we get a problem with collision of two revisions having
    # the same timestamp
    time.sleep(1)

    # create another revision
    diffrunner.scan_files_for_changes()

    return store, notes_dir

def manualtest__generation__basic1():
    store, notes_dir = setup_revisions_notes1()

    # check for two revisions, second one only has third line modified 
    rev_objs = store.get_revisions_for_document_path_sorted("notes1.txt")

    assert len(rev_objs) == 2

    generator = StaticHtmlGenerator(store.config, store)

    # normally we'd have filtered the rev_objs for dates, but no point here

    generator.generate_pages_and_index_for_revisions(rev_objs)

    print "MANUAL TEST: verify content of generation dir"

    # this being a manual test, we don't remove temp dirs
    #shutil.rmtree(notes_dir)
    #teardown_temp_db(store)
 
if __name__ == '__main__':
    manualtest__generation__basic1()

