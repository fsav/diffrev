diffrev
=======

Tool to review notes written in text files, to facilitate memorization, inspired by spaced repetition. Instead of reviewing flashcards, you review the diffs from the text files. See blog post here:

https://www.fsavard.com/flow/2012/12/diff-revision/

Please see diffrevision.py (just run it without arguments) for usage.

Changelog
---------

* 2012-12-19: added a local server, and a column to the 'revisions' table in the SQLite database. If anyone downloaded prior to this date, you need to run the following ALTER TABLE in an sqlite client, to update your db.sqlite database:

  ALTER TABLE revisions ADD hidden INTEGER NOT NULL DEFAULT 0;

  If you've downloaded after that, don't worry about it, the column is now created by default.

