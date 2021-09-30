# CosFormatter - Services for formatting data for consanguinity gramplet
#
# Copyright (C) 2021  Hans Boldt
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""
Module consformatter.py

Services for formatting data for consanguinity gramplet

Exports:

class ConsFormatter
class SimpleStringBuffer

"""

#-------------------#
# Python modules    #
#-------------------#
from html import escape
from math import log
from itertools import chain
# import pdb

#-------------------#
# Gramps modules    #
#-------------------#
from gramps.gen.lib import Person, EventType
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.datehandler import get_date
from gramps.gen.relationship import get_relationship_calculator
from gramps.gen.utils.db import (get_birth_or_fallback, get_death_or_fallback)
from gramps.gen.config import config
from gramps.gen.utils.symbols import Symbols
from gramps.gen.const import GRAMPS_LOCALE as glocale

#-----------------------------------#
# Other related gramplet modules    #
#-----------------------------------#
from pedigree import Pedigree

#------------------#
# Translation      #
#------------------#
try:
    _trans = glocale.get_addon_translator(__file__)
    _ = _trans.gettext
except ValueError:
    _ = glocale.translation.sgettext
ngettext = glocale.translation.ngettext # else "nearby" comments are ignored


#-------------#
# Messages    #
#-------------#
MSG_UNKNOWN_NAME = _('(unknown)')
MSG_RELATIONSHIP = _('Relationship:')
MSG_RELATIONSHIPS = _('Relationships:')
MSG_COMMON_ANC = _('"Common ancestor:')
MSG_COMMON_ANCS = _('Common ancestors:')
MSG_MORE_SPOUSE_RELS = _('More spouse relationships not shown.')
MSG_MORE_RELS = _('More relationships not shown.')
MSG_PED_COLLAPSE_ACTIVE = _('Pedigree collapse for active person')
MSG_NO_PED_COLLAPSE = _('No pedigree collapse found.')
MSG_PED_COLLAPSE_AT = _('Pedigree collapse at %(relationship)s:')
MSG_MORE_PED_COLLAPSE = _('More instances of pedigree collapse not shown.')
MSG_NO_PARTNERS = _('No partners.')
MSG_NOT_MARRIED = _('Not married.')
MSG_PARTNER = _('Partner:')
MSG_RELS_BET_ACTIVE_AND_PARTNER = \
          _('Relationships between active person and partners')
MSG_NO_COMMON_ANCS = _('No common ancestors found.')
MSG_MORE_ANCESTORS = _('More ancestors not shown.')


TITLE_FORMAT = '<span size="larger" weight="bold" underline="single">%s</span>'

PED_COLLAPSE_LIMIT = 10
RELATIONSHIP_LIMIT = 8


#------------------------------#
#                              #
# SimpleStringBuffer class     #
#                              #
#------------------------------#
class SimpleStringBuffer:
    """
    Simple string buffer
    """
    __slots__ = ['buffer']

    def __init__(self, string=None):
        """
        init()
        """
        self.buffer = list()
        if string:
            self.buffer.append(string)

    def __add__(self, string):
        """
        Append string to buffer
        """
        self.buffer.append(string)
        return self

    def __str__(self):
        """
        Convert buffer to string
        """
        return ''.join(self.buffer)


#------------------------------#
#                              #
# CosFormatter class           #
#                              #
#------------------------------#
class ConsFormatter:
    """
    Methods for formatting the consanguinity data.
    """

    # class variables
    relcalc = get_relationship_calculator()
    symbols = config.get('utf8.in-use')
    if symbols:
        syms = Symbols()
        death_symbols = syms.get_death_symbols()
        death_symbol = config.get('utf8.death-symbol')
        birth_symbol = syms.get_symbol_for_string(Symbols.SYMBOL_BIRTH)
        baptism_symbol = syms.get_symbol_for_string(Symbols.SYMBOL_BAPTISM)
        death_symbol = death_symbols[death_symbol][1]
        burial_symbol = syms.get_symbol_for_string(Symbols.SYMBOL_BURIED)
    else:
        birth_symbol = '*'
        baptism_symbol = '~'
        death_symbol = '+'
        burial_symbol = '[]'


    def __init__(self, db, person_handle, pedigree, spouse_pedigrees):
        """
        __init__()
        """
        self.db = db
        self.person_handle = person_handle
        self.pedigree = pedigree
        self.spouse_pedigrees = spouse_pedigrees
        self.person = self.db.get_person_from_handle(person_handle)
        self.gender = self.person.get_gender()


    def get_title(self):
        """
        Format title
        """
        return self.format_person(self.db, self.person_handle,
                                  '<span size="larger" weight="ultrabold">',
                                  '</span>', link=False)


    def get_pedigree_collapse(self):
        """
        Format the pedigree collapse section
        """
        outstr = SimpleStringBuffer((TITLE_FORMAT % MSG_PED_COLLAPSE_ACTIVE)
                                    + "\n\n")

        # Any pedigree collapse?
        if not self.pedigree.has_pedigree_collapse():
            outstr += "<i>" + MSG_NO_PED_COLLAPSE + "</i>\n\n"
            return str(outstr)

        # List out ancestors who were cousins
        ped_collapse = self.pedigree.determine_pedigree_collapse()

        count = 0
        for descnum in sorted(ped_collapse.keys()):
            count += 1
            if count > PED_COLLAPSE_LIMIT:
                outstr += "<b><i>" + MSG_MORE_PED_COLLAPSE + "</i></b>\n"
                break

            comm_anc = ped_collapse[descnum]

            # Process one common descendant
            father_handle = self.pedigree.get_ancestor_by_number(descnum*2) \
                                .get_person_handle()
            mother_handle = self.pedigree.get_ancestor_by_number(descnum*2+1) \
                                .get_person_handle()

            gens = int(log(descnum, 2)) + 1
            rel = self.relcalc.get_plural_relationship_string(gens, 0)
            outstr += "<b>" + MSG_PED_COLLAPSE_AT % {'relationship': rel} \
                      + "</b>\n"

            # Print names of ancestors where pedigree collapse occurs
            outstr += self.format_person(self.db, father_handle, "\t", "\n")
            outstr += self.format_person(self.db, mother_handle, "\t", "\n")

            # Order the common ancestors list by primary ancestor numbers
            ordered_anc = self.pedigree.order_ancestor_list(comm_anc)
            for (primnums, ancs) in ordered_anc.items():
                outstr += self.format_common_anc_rels \
                            (0, ancs, (True if len(primnums) == 1 else False),
                             gens, Person.MALE, Person.FEMALE)
                outstr += self.format_common_ancestor_names(self.pedigree,
                                                            primnums)

            outstr += "\n"

        return str(outstr)


    def get_consanguinity(self):
        """
        Format the consanguinity section
        """

        outstr = SimpleStringBuffer((TITLE_FORMAT
                                     % MSG_RELS_BET_ACTIVE_AND_PARTNER) + "\n")

        if not self.spouse_pedigrees:
            return str(outstr + "\n<i>"
                       + self.no_spouses_string(self.person) + "</i>\n")

        # Go through spouses
        spouse_num = 0
        for (spouse_handle, spouse_pedigree) in self.spouse_pedigrees:
            # Get and print info for spouse
            spouse_num += 1
            spouse = self.db.get_person_from_handle(spouse_handle)
            spouse_gender = spouse.get_gender()
            outstr += self.format_person(self.db, spouse_handle,
                                         "\n<b>" + MSG_PARTNER + "</b> ", "\n")

            if not spouse_pedigree.has_pedigree_collapse():
                outstr += "\t<i>" + MSG_NO_COMMON_ANCS + "</i>\n"
                continue

            # Look for pedigree collapse where common descendant is #1
            ped_collapse = spouse_pedigree.determine_pedigree_collapse(1)
            if not ped_collapse:
                outstr += "\t<i>" + MSG_NO_COMMON_ANCS + "</i>\n"
                continue

            # We have relationship between active person and spouse
            ordered_anc = spouse_pedigree.order_ancestor_list(ped_collapse[1])

            count = 0
            for (primnums, ancs) in ordered_anc.items():
                count += 1
                if count > PED_COLLAPSE_LIMIT:
                    outstr += "\t<b><i>" + MSG_MORE_SPOUSE_RELS + "</i></b>\n"
                    break

                outstr += self.format_common_anc_rels \
                                (spouse_num, ancs,
                                 (True if len(primnums) == 1 else False),
                                 1, self.gender, spouse_gender)
                outstr += self.format_common_ancestor_names(spouse_pedigree,
                                                            primnums)

        return str(outstr)


    def format_common_ancestor_names(self, pedigree, common_ancestors):
        """
        Print out the names of one set of common ancestors.
        """
        outstr = SimpleStringBuffer()
        if len(common_ancestors) == 1:
            outstr += "\t<b>" + MSG_COMMON_ANC + "</b>\n"
        else:
            outstr += "\t<b>" + MSG_COMMON_ANCS + "</b>\n"

        for anc_num in common_ancestors:
            ancestor = pedigree.get_ancestor_by_number(anc_num)
            outstr += self.format_person(self.db,
                                         ancestor.get_person_handle(),
                                         "\t\t", "\n")
        return str(outstr)


    def format_common_anc_rels(self, ped_index,
                               rel, half, generations,
                               active_gender, spouse_gender):
        """
        Print out list of ancestor relationships.
        """
        outstr = SimpleStringBuffer()

        # Count number of relationships
        relnums = rel.keys()
        plural = (len(relnums) > 1)
        if plural:
            outstr += "\t<b>" + MSG_RELATIONSHIPS + '</b> '
            tabs = "\n\t\t\t"
        else:
            outstr += "\t<b>" + MSG_RELATIONSHIP + '</b> '
            tabs = ''

        relfun = self.relcalc.get_plural_relationship_string
        rel_type = ' ½' if half else ''

        # Loop through all relationships
        count = 0
        for relnum in relnums:
            count += 1
            if count > RELATIONSHIP_LIMIT:
                outstr += "\t\t\t<b><i>" + MSG_MORE_RELS + "</i></b>\n"
                break

            rellist = rel[relnum]
            num_rels = len(rellist)
            ways = (" x%d" % num_rels) if num_rels > 1 else ''

            if active_gender == Person.MALE:
                relstr = relfun(relnum[0] - generations, relnum[1] - generations)
            else:
                relstr = relfun(relnum[1] - generations, relnum[0] - generations)

            relstr = "%(relationship)s%(separator)s%(half)s%(ways)s" %  \
                    {'relationship': relstr,
                     'separator': (',' if half or ways else ''),
                     'half': rel_type,
                     'ways': ways}

            # Format relationship as clickable link
            rellist_str = ''
            for item in rellist:
                rellist_str += ','.join([str(x) for x in chain.from_iterable(item)]) + ' '
            href = 'N %d %s' % (ped_index, rellist_str)
            outstr += tabs + '<a href="%s">%s</a>\n' % (href, relstr)

            tabs = "\t\t\t"

        return str(outstr)


    def no_spouses_string(self, person):
        """
        Determine if there are no spouses because person never married.
        """
        # Look for death event, and then look for "unmarried" attribute.
        death_event = get_death_or_fallback(self.db, person)
        if not death_event:
            return MSG_NO_PARTNERS

        event_type = death_event.get_type()
        if event_type != EventType.DEATH:
            return MSG_NO_PARTNERS

        attr_list = death_event.get_attribute_list()
        for attr in attr_list:
            if attr.get_type().string.upper() == 'UNMARRIED':
                return MSG_NOT_MARRIED

        return MSG_NO_PARTNERS


    @classmethod
    def format_person(cls, db, person_handle, prestr='', poststr='',
                      link=True, dates=True, split=False):
        """
        Print out person.
        """
        if person_handle:
            person = db.get_person_from_handle(person_handle)
            name = name_displayer.display_name(person.get_primary_name())
        else:
            name = MSG_UNKNOWN_NAME
            dates = False

        if link:
            outstr = '<a href="P %s">%s</a>' % (person_handle, name)
        else:
            outstr = name

        if dates:
            datestr = cls.info_string(db, person, split)
            if datestr:
                outstr += ("\n" if split else ' ') + datestr

        return prestr + outstr + poststr


    @classmethod
    def info_string(cls, db, person, split=False):
        """
        Information string for a person, including date of birth (or baptism)
        and date of death (or burial).
        """
        bdate = cls.fmt_date(get_birth_or_fallback(db, person),
                             EventType.BIRTH)
        ddate = cls.fmt_date(get_death_or_fallback(db, person),
                             EventType.DEATH)

        if split:
            if bdate and ddate:
                return "%s\n%s" % (bdate, ddate)
            return bdate if bdate else ddate if ddate else ''

        if bdate and ddate:
            return "(%s, %s)" % (bdate, ddate)
        if bdate:
            return "(%s)" % (bdate)
        if ddate:
            return "(%s)" % (ddate)
        return ''


    @classmethod
    def fmt_date(cls, date, preferred_event_type):
        """
        Format the given date.
        """
        if not date:
            return ''
        sdate = get_date(date)
        if not sdate:
            return ''

        sdate = escape(sdate)
        date_type = date.get_type()
        if preferred_event_type == EventType.BIRTH:
            if date_type != preferred_event_type:
                return "%s<i>%s</i>" % (cls.baptism_symbol, sdate)
            return "%s%s" % (cls.birth_symbol, sdate)

        if date_type != preferred_event_type:
            return "%s<i>%s</i>" % (cls.burial_symbol, sdate)
        return "%s%s" % (cls.death_symbol, sdate)
