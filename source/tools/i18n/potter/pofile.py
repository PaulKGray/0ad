# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2011 Edgewall Software
# Copyright (C) 2013 Wildfire Games
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
# following conditions are met:
#
#   Redistributions of source code must retain the above copyright notice, this list of conditions and the following
#   disclaimer.
#   Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following
#   disclaimer in the documentation and/or other materials provided with the distribution.
#   The name of the author may not be used to endorse or promote products derived from this software without specific
#   prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR “AS IS” AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs:
# • http://babel.edgewall.org/log/trunk/babel/messages
# • http://trac.wildfiregames.com/browser/ps/trunk/source/tools/i18n/potter

"""Reading and writing of files in the ``gettext`` PO (portable object)
format.

:see: `The Format of PO Files
       <http://www.gnu.org/software/gettext/manual/gettext.html#PO-Files>`_
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime
import os
import re

from potter.util import wraptext
from potter.catalog import Catalog, Message

__all__ = ['read_po', 'write_po']
__docformat__ = 'restructuredtext en'




def unescape(string):
    r"""Reverse `escape` the given string.

    >>> print unescape('"Say:\\n  \\"hello, world!\\"\\n"')
    Say:
      "hello, world!"
    <BLANKLINE>

    :param string: the string to unescape
    """
    def replace_escapes(match):
        m = match.group(1)
        if m == 'n':
            return '\n'
        elif m == 't':
            return '\t'
        elif m == 'r':
            return '\r'
        # m is \ or "
        return m
    return re.compile(r'\\([\\trn"])').sub(replace_escapes, string[1:-1])


def denormalize(string):
    r"""Reverse the normalization done by the `normalize` function.

    >>> print denormalize(r'''""
    ... "Say:\n"
    ... "  \"hello, world!\"\n"''')
    Say:
      "hello, world!"
    <BLANKLINE>

    >>> print denormalize(r'''""
    ... "Say:\n"
    ... "  \"Lorem ipsum dolor sit "
    ... "amet, consectetur adipisicing"
    ... " elit, \"\n"''')
    Say:
      "Lorem ipsum dolor sit amet, consectetur adipisicing elit, "
    <BLANKLINE>

    :param string: the string to denormalize
    """
    if '\n' in string:
        escaped_lines = string.splitlines()
        if string.startswith('""'):
            escaped_lines = escaped_lines[1:]
        lines = map(unescape, escaped_lines)
        return ''.join(lines)
    else:
        return unescape(string)

def read_po(fileobj, locale=None, domain=None, ignore_obsolete=False, charset="utf-8"):
    """Read messages from a ``gettext`` PO (portable object) file from the given
    file-like object and return a `Catalog`.

    >>> from datetime import datetime
    >>> from StringIO import StringIO
    >>> buf = StringIO('''
    ... #: main.py:1
    ... #, fuzzy, python-format
    ... msgid "foo %(name)s"
    ... msgstr "quux %(name)s"
    ...
    ... # A user comment
    ... #. An auto comment
    ... #: main.py:3
    ... msgid "bar"
    ... msgid_plural "baz"
    ... msgstr[0] "bar"
    ... msgstr[1] "baaz"
    ... ''')
    >>> catalog = read_po(buf)
    >>> catalog.revision_date = datetime(2007, 04, 01)

    >>> for message in catalog:
    ...     if message.id:
    ...         print (message.id, message.string)
    ...         print ' ', (message.locations, message.flags)
    ...         print ' ', (message.user_comments, message.auto_comments)
    (u'foo %(name)s', u'quux %(name)s')
      ([(u'main.py', 1)], set([u'fuzzy', u'python-format']))
      ([], [])
    ((u'bar', u'baz'), (u'bar', u'baaz'))
      ([(u'main.py', 3)], set([]))
      ([u'A user comment'], [u'An auto comment'])

    .. versionadded:: 1.0
       Added support for explicit charset argument.

    :param fileobj: the file-like object to read the PO file from
    :param locale: the locale identifier or `Locale` object, or `None`
                   if the catalog is not bound to a locale (which basically
                   means it's a template)
    :param domain: the message domain
    :param ignore_obsolete: whether to ignore obsolete messages in the input
    :param charset: the character set of the catalog.
    """
    catalog = Catalog(locale=locale, domain=domain, charset=charset)

    counter = [0]
    offset = [0]
    messages = []
    translations = []
    locations = []
    flags = []
    user_comments = []
    auto_comments = []
    obsolete = [False]
    context = []
    in_msgid = [False]
    in_msgstr = [False]
    in_msgctxt = [False]

    def _add_message():
        translations.sort()
        if len(messages) > 1:
            msgid = tuple([denormalize(m) for m in messages])
        else:
            msgid = denormalize(messages[0])
        if isinstance(msgid, (list, tuple)):
            string = []
            for idx in range(catalog.num_plurals):
                try:
                    string.append(translations[idx])
                except IndexError:
                    string.append((idx, ''))
            string = tuple([denormalize(t[1]) for t in string])
        else:
            string = denormalize(translations[0][1])
        if context:
            msgctxt = denormalize('\n'.join(context))
        else:
            msgctxt = None
        message = Message(msgid, string, list(locations), set(flags),
                          auto_comments, user_comments, lineno=offset[0] + 1,
                          context=msgctxt)
        if obsolete[0]:
            if not ignore_obsolete:
                catalog.obsolete[msgid] = message
        else:
            catalog[msgid] = message
        del messages[:]; del translations[:]; del context[:]; del locations[:];
        del flags[:]; del auto_comments[:]; del user_comments[:];
        obsolete[0] = False
        counter[0] += 1

    def _process_message_line(lineno, line):
        if line.startswith('msgid_plural'):
            in_msgid[0] = True
            msg = line[12:].lstrip()
            messages.append(msg)
        elif line.startswith('msgid'):
            in_msgid[0] = True
            offset[0] = lineno
            txt = line[5:].lstrip()
            if messages:
                _add_message()
            messages.append(txt)
        elif line.startswith('msgstr'):
            in_msgid[0] = False
            in_msgstr[0] = True
            msg = line[6:].lstrip()
            if msg.startswith('['):
                idx, msg = msg[1:].split(']', 1)
                translations.append([int(idx), msg.lstrip()])
            else:
                translations.append([0, msg])
        elif line.startswith('msgctxt'):
            if messages:
                _add_message()
            in_msgid[0] = in_msgstr[0] = False
            context.append(line[7:].lstrip())
        elif line.startswith('"'):
            if in_msgid[0]:
                messages[-1] += u'\n' + line.rstrip()
            elif in_msgstr[0]:
                translations[-1][1] += u'\n' + line.rstrip()
            elif in_msgctxt[0]:
                context.append(line.rstrip())

    for lineno, line in enumerate(fileobj.readlines()):
        line = line.strip()
        if not isinstance(line, unicode):
            line = line.decode(catalog.charset)
        if line.startswith('#'):
            in_msgid[0] = in_msgstr[0] = False
            if messages and translations:
                _add_message()
            if line[1:].startswith(':'):
                for location in line[2:].lstrip().split():
                    pos = location.rfind(':')
                    if pos >= 0:
                        try:
                            lineno = int(location[pos + 1:])
                        except ValueError:
                            continue
                        locations.append((location[:pos], lineno))
            elif line[1:].startswith(','):
                for flag in line[2:].lstrip().split(','):
                    flags.append(flag.strip())
            elif line[1:].startswith('~'):
                obsolete[0] = True
                _process_message_line(lineno, line[2:].lstrip())
            elif line[1:].startswith('.'):
                # These are called auto-comments
                comment = line[2:].strip()
                if comment: # Just check that we're not adding empty comments
                    auto_comments.append(comment)
            else:
                # These are called user comments
                user_comments.append(line[1:].strip())
        else:
            _process_message_line(lineno, line)

    if messages:
        _add_message()

    # No actual messages found, but there was some info in comments, from which
    # we'll construct an empty header message
    elif not counter[0] and (flags or user_comments or auto_comments):
        messages.append(u'')
        translations.append([0, u''])
        _add_message()

    return catalog

WORD_SEP = re.compile('('
    r'\s+|'                                 # any whitespace
    r'[^\s\w]*\w+[a-zA-Z]-(?=\w+[a-zA-Z])|' # hyphenated words
    r'(?<=[\w\!\"\'\&\.\,\?])-{2,}(?=\w)'   # em-dash
')')

def escape(string):
    r"""Escape the given string so that it can be included in double-quoted
    strings in ``PO`` files.

    >>> escape('''Say:
    ...   "hello, world!"
    ... ''')
    '"Say:\\n  \\"hello, world!\\"\\n"'

    :param string: the string to escape
    :return: the escaped string
    :rtype: `str` or `unicode`
    """
    return '"%s"' % string.replace('\\', '\\\\') \
                          .replace('\t', '\\t') \
                          .replace('\r', '\\r') \
                          .replace('\n', '\\n') \
                          .replace('\"', '\\"')

def normalize(string, prefix='', width=80):
    r"""Convert a string into a format that is appropriate for .po files.

    >>> print normalize('''Say:
    ...   "hello, world!"
    ... ''', width=None)
    ""
    "Say:\n"
    "  \"hello, world!\"\n"

    >>> print normalize('''Say:
    ...   "Lorem ipsum dolor sit amet, consectetur adipisicing elit, "
    ... ''', width=32)
    ""
    "Say:\n"
    "  \"Lorem ipsum dolor sit "
    "amet, consectetur adipisicing"
    " elit, \"\n"

    :param string: the string to normalize
    :param prefix: a string that should be prepended to every line
    :param width: the maximum line width; use `None`, 0, or a negative number
                  to completely disable line wrapping
    :return: the normalized string
    :rtype: `unicode`
    """
    if width and width > 0:
        prefixlen = len(prefix)
        lines = []
        for line in string.splitlines(True):
            if len(escape(line)) + prefixlen > width:
                chunks = WORD_SEP.split(line)
                chunks.reverse()
                while chunks:
                    buf = []
                    size = 2
                    while chunks:
                        l = len(escape(chunks[-1])) - 2 + prefixlen
                        if size + l < width:
                            buf.append(chunks.pop())
                            size += l
                        else:
                            if not buf:
                                # handle long chunks by putting them on a
                                # separate line
                                buf.append(chunks.pop())
                            break
                    lines.append(u''.join(buf))
            else:
                lines.append(line)
    else:
        lines = string.splitlines(True)

    if len(lines) <= 1:
        return escape(string)

    # Remove empty trailing line
    if lines and not lines[-1]:
        del lines[-1]
        lines[-1] += '\n'
    return u'""\n' + u'\n'.join([(prefix + escape(l)) for l in lines])

def write_po(fileobj, catalog, width=80, no_location=False, omit_header=False,
             sort_output=False, sort_by_file=False, ignore_obsolete=False,
             include_previous=False):
    r"""Write a ``gettext`` PO (portable object) template file for a given
    message catalog to the provided file-like object.

    >>> catalog = Catalog()
    >>> catalog.add(u'foo %(name)s', locations=['main.py:1',],
    ...             flags=('fuzzy',))
    <Message...>
    >>> catalog.add((u'bar', u'baz'), locations=['main.py:3',])
    <Message...>
    >>> from StringIO import StringIO
    >>> buf = StringIO()
    >>> write_po(buf, catalog, omit_header=True)
    >>> print buf.getvalue()
    #: main.py:1
    #, fuzzy, python-format
    msgid "foo %(name)s"
    msgstr ""
    <BLANKLINE>
    #: main.py:3
    msgid "bar"
    msgid_plural "baz"
    msgstr[0] ""
    msgstr[1] ""
    <BLANKLINE>
    <BLANKLINE>

    :param fileobj: the file-like object to write to
    :param catalog: the `Catalog` instance
    :param width: the maximum line width for the generated output; use `None`,
                  0, or a negative number to completely disable line wrapping
    :param no_location: do not emit a location comment for every message
    :param omit_header: do not include the ``msgid ""`` entry at the top of the
                        output
    :param sort_output: whether to sort the messages in the output by msgid
    :param sort_by_file: whether to sort the messages in the output by their
                         locations
    :param ignore_obsolete: whether to ignore obsolete messages and not include
                            them in the output; by default they are included as
                            comments
    :param include_previous: include the old msgid as a comment when
                             updating the catalog
    """
    def _normalize(key, prefix=''):
        return normalize(key, prefix=prefix, width=width)

    def _write(text):
        fileobj.write(text)

    def _write_comment(comment, prefix=''):
        # xgettext always wraps comments even if --no-wrap is passed;
        # provide the same behaviour
        if width and width > 0:
            _width = width
        else:
            _width = 80
        if isinstance(comment, (tuple, list)):
            commentText = str(comment[0])
            for piece in comment[1:]:
                commentText += ":" + str(piece)
            comment = commentText
        for line in wraptext(comment, _width):
            _write('#%s %s\n' % (prefix, line.strip()))

    def _write_message(message, prefix=''):
        if isinstance(message.id, (list, tuple)):
            if message.context:
                _write('%smsgctxt %s\n' % (prefix,
                                           _normalize(message.context, prefix)))
            _write('%smsgid %s\n' % (prefix, _normalize(message.id[0], prefix)))
            _write('%smsgid_plural %s\n' % (
                prefix, _normalize(message.id[1], prefix)
            ))

            for idx in range(2):
                try:
                    string = message.string[idx]
                except IndexError:
                    string = ''
                _write('%smsgstr[%d] %s\n' % (
                    prefix, idx, _normalize(string, prefix)
                ))
        else:
            if message.context:
                _write('%smsgctxt %s\n' % (prefix,
                                           _normalize(message.context, prefix)))
            _write('%smsgid %s\n' % (prefix, _normalize(message.id, prefix)))
            _write('%smsgstr %s\n' % (
                prefix, _normalize(message.string or '', prefix)
            ))

    messages = list(catalog)
    if sort_output:
        messages.sort()
    elif sort_by_file:
        messages.sort(lambda x,y: cmp(x.locations, y.locations))

    for message in messages:
        if not message.id: # This is the header "message"
            if omit_header:
                continue
            comment_header = catalog.header_comment
            if width and width > 0:
                lines = []
                for line in comment_header.splitlines():
                    lines += wraptext(line, width=width,
                                      subsequent_indent='# ')
                comment_header = u'\n'.join(lines)
            _write(comment_header + u'\n')

        for comment in message.user_comments:
            _write_comment(comment)
        for comment in message.auto_comments:
            _write_comment(comment, prefix='.')

        if not no_location:
            for location in message.locations:
                _write_comment(location, prefix=':')
        if message.flags:
            _write('#%s\n' % ', '.join([''] + list(message.flags)))

        if message.previous_id and include_previous:
            _write_comment('msgid %s' % _normalize(message.previous_id[0]),
                           prefix='|')
            if len(message.previous_id) > 1:
                _write_comment('msgid_plural %s' % _normalize(
                    message.previous_id[1]
                ), prefix='|')

        _write_message(message)
        _write('\n')

    if not ignore_obsolete:
        for message in catalog.obsolete.values():
            for comment in message.user_comments:
                _write_comment(comment)
            _write_message(message, prefix='#~ ')
            _write('\n')
