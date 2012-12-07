import Exporters
import WikiSyntax
import WikiFormatting
from StringOps import escapeHtml

import re

# This formatter is a HUGE hack. And by 'hack' I mean in the purest form
# as in "hacked together in two hours". Here's what happened:
#
# - I wanted something to format my .wiki files for export offline (ie.
#     without WikidPad loaded)
# - So I thought I could write the basics of a parser for 'easy' stuff
#     such as bold, titles, urls, lists, etc. in a few hours
#     (naive as I tend to be)
# - So I took a quick look at WP 1.8 parser for inspiration, only to
#     realize the foolishness of my endeavour (too much details involved)
# - Then it dawned upon me that WP is open source
# - Which led me to extracting the non wx-and-whatnot dependent part of WP
#     which means (VERY) crudely removing most of the "advanced" parts of
#     the parser, the ones that rely on the Wiki Structure, on plugins etc.
#
# More specifically, the parts/features removed mean:
# - no configuration of colors on pages, or usage of page attributes
# - no wikiword linking
# - no extension such as [:page:]
# - no properties such as anchor: 
# - no footnotes_as_wikiwords (whatever that is)
# 
# But I _do_ get a crude offline formatter out of 2 hours of delicately 
# slashing this (somewhat older... WP is at 2.2 now?) code with a chainsaw.
#
# I tried looking at using WP 2.2's code, but it seems more complex to extract
# the bits I want.

empty_line_re = re.compile(r"\s*$")
bullet_re = re.compile(r"(\s*)((\d+\.)|\*) (.*)")
title_re = re.compile(r"^\++.*")

pre_start_re = re.compile(r"^([ \t]*<<pre[ \t]*)$")
pre_end_re = re.compile(r"^([ \t]*>>[ \t]*)$")

postprocess_replacements = [\
        ("\n<span class='hl'><br />\n",'\n'),
        ("\n</span><br />\n","\n")]

class WikidpadFormatter():
    def __init__(self, config):
        self.config = config
        self.formatting = WikiFormatting.WikiFormatting(WikiSyntax)

    def export_with_wikidpad_engine(self, content):
        exporter = Exporters.HtmlXmlExporter()
        image_base_dir = getattr(self.config, 'wikidpad_files_base_dir', '')
        return exporter.formatContent(content, None, self.formatting, image_base_dir)

    # preprocessing to put highlight <span>s in the right places and avoid
    # messing the wiki formatting
    # An important point is that we must add the \n manually, as we want tight
    # control over adding whitespace (otw too much space between lines)
    def highlight_lines_in_page(self, text_lines, line_nums):
        for lineno,line in enumerate(text_lines):
            line = line.rstrip()

            is_pre_start = pre_start_re.match(line)
            is_pre_end = pre_end_re.match(line)

            if lineno in line_nums\
                    and not (is_pre_start or is_pre_end)\
                    and line != "":
                # for bullet lists, we want to avoid wrapping the <li></li>
                # inside a <span> pair, so we must take extra steps
                m = bullet_re.match(line)
                if m:
                    text_lines[lineno] = m.group(1) + m.group(2) +\
                        " <span class='hl'>" + \
                        m.group(4).rstrip() + \
                        "</span>\n"
                    continue

                # for titles, the solution is simple: just add two lines wrapping
                # the original, and it won't make a difference in the HTML
                m = title_re.match(line)
                if m or lineno==0:
                    # the space between > and the \n is important here, otw
                    # the Exporter will remove the line
                    text_lines[lineno] = "<div class='hl'> \n" + \
                            line + \
                            "\n</div> \n"
                    continue

                text_lines[lineno] = "<span class='hl'>" + line + "</span>\n"
            else:
                # no change, or empty line, just add the \n
                text_lines[lineno] += "\n"

        return text_lines

    # correct for too much spacing, ...well, do what we can anyway...
    def postprocess(self, content):
        # compensate for mess inside <<pre>>
        # yes this means you can't type this in your wiki...
        content = content.replace("&lt;span class='hl'&gt;", "<span class='hl'>")
        content = content.replace("&lt;/span&gt;", "</span>")

        # now title divs being added a br
        content = content.replace("<div class='hl'> <br />", "<div class='hl'>")
        content = content.replace("</div> <br />", "</div>")

        for rem in postprocess_replacements:
            content = content.replace(rem[0], rem[1])
        return content

    def format(self, rev_obj):
        str_line_nos = rev_obj.changelist.splitlines()
        line_nos_with_changes = [int(lineno) for lineno in str_line_nos]

        orig_lines = rev_obj.content.splitlines()
        try:
            new_lines = self.highlight_lines_in_page(\
                            orig_lines,
                            line_nos_with_changes)
        except RuntimeError, m:
            print m
            print "(in file ", rev_obj.document_relative_path

        content  = self.export_with_wikidpad_engine("".join(new_lines))
        content = self.postprocess(content)


        return content



##############################################################################
# tests

content1 = """+ MyDoc

++ My second title

+++ My third title

* list
    * list 2
        * list 3
        * list 4

1. num 1
    1. num 2
    1. num 3
        1. num 4
    1. num 5

rel://files/signal_processing_jpeg_matrix.png

<<pre
pre content & * < \ 
on two lines
>>

    """

def test_format_basic():
    class FakeConfig(object):
        def __init__(self):
            self.image_base_dir = '/foo/bar'

    class FakeRevObj(object):
        def __init__(self, content, changelist=None):
            self.content = content
            if changelist:
                self.changelist = changelist
            else:
                self.changelist = "\n".join([str(i) for i in range(len(self.content))])

    formatter = WikidpadFormatter(config=FakeConfig())
    
    rev_obj = FakeRevObj(content1)

    print formatter.format(rev_obj)

if __name__ == '__main__':
    test_format_basic()

