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

from difflib import Differ
import cgi

def get_changelist(old_text, new_text):
    # copy and make sure we don't register changes simply
    # because the endline characters changed (which happens
    # when syncing windows and linux files, and when an otw
    # unchanged line at the end of the file now has an endline
    # character)
    # splitlines() eliminate the last line if it's empty, and
    # removes the endline characters, so they won't be considered
    # for the diffs
    old_text = old_text.splitlines()
    old_text = [l for l in old_text]

    new_text = new_text.splitlines()
    new_text = [l for l in new_text]

    lines_with_changes = None

    differ = Differ()
    differ_output = differ.compare(old_text, new_text)

    lc = 0
    lines_with_changes = []
    for l in differ_output:
        if l[0] == '+':
            lines_with_changes.append(lc)
            lc += 1
        elif l[0] == '-':
            pass
        elif l[0] == ' ':
            lc += 1
        # there might also be the '?' case, but this doesn't affect the linecount
    
    return "\n".join([str(l) for l in lines_with_changes])

###################
# tests

def test__get_changelist__basic():
    text1 = "This is some\r\nMulti-line DOS-breaklined\r\ntext.\r\n"
    text2 = "This is some\r\nMulti-line DOS-breaklined\r\ntext. With additions\r\nto these lines"

    assert get_changelist(text1, text2) == '2\n3';
    # deleted one line 
    assert get_changelist(text2, text1) == '2';

def test__get_changelist__no_change_for_eolchange():
    text1 = "This is some\r\nMulti-line DOS-breaklined"
    text2 = "This is some\r\nMulti-line DOS-breaklined\r\n"

    assert get_changelist(text1, text2) == '';
    assert get_changelist(text2, text1) == '';

if __name__ == '__main__':
    test__get_changelist__basic()
    test__get_changelist__no_change_for_eolchange()

