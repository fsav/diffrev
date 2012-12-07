"""
This module provides revision pages generation functionality.

The sequence for the transformation of a single page is in the form of a
transformation pipeline.

The pipeline input is a set of lines for the un-highlighted content. For each
line, a set of "spans" will gradually be added. Spans are made of a pair of
line positions (relative to the original line) and opening/closing tags to be
inserted at those positions.

Example modules for this pipeline are, notably:
- "highlighters" which add code corresponding to revision highlights
- "syntax compilers" which allow wiki-like formatting rules to be transformed
  into their HTML equivalent

A module may also transform the lines themselves, but then it must take care
to update the positions in the spans associated with the line up to now.

This "span" concept and way of doing things is an attempt at a
solution to the problem of having modules not depend on one another while
at the same time transforming a line with their own independent syntaxes.
This independence is hard to achieve if modules must take into account each
other's changes to this line. I don't know how well this will work out in the
end...

At the end of this pipeline, some functions in static_html_generator take in
the lines and the spans and insert those spans at the right places, taking
into account changes in line positions due to earlier spans in the list for
a given line. This may involve breaking some spans into sub-spans if there 
is overlap, but is TBD for the moment.
"""

