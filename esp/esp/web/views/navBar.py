
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@lists.learningu.org
"""
from esp.web.models import NavBarEntry, NavBarCategory
from esp.users.models import UserBit, AnonymousUser, ESPUser
from esp.datatree.models import *
from django.http import HttpResponseRedirect, Http404, HttpResponse
from esp.datatree.models import *
from esp.dblog.models import error
from esp.middleware.esperrormiddleware import ESPError

from esp.program.models import Program
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.db.models.query import Q

EDIT_VERB_STRING = 'V/Administer/Edit/QSD'

class LazyNavBar(object):
    """ Class which lazily evaluates the context for rendering a nav bar. """
    def __init__(self, user, node, section, category):
        self.user = user
        self.node = node
        self.section = section
        self.category = category

    def _value(self):
        user = ESPUser(self.user)
        node = self.node

        if not self.category:
            self.category = nav_category(node, section)

        if user:
            has_edit_bits = user.isAdministrator()
        else:
            has_edit_bits = False

        navbars = list(self.category.get_navbars().order_by('sort_rank'))
        navbar_context = [{'entry': x, 'has_bits': has_edit_bits} for x in navbars]
        print "==============", navbar_context
        context = { 'node': node,
                    'has_edit_bits': has_edit_bits,
                    'entries': navbar_context,
                    'section': section
                    }

        return context

    value = property(_value)


def nav_category(node, section=''):
    """ A function to guess the appropriate navigation category when one
        is not provided in the context. """
        
    #   First, try finding a category with an appropriate tree anchor.
    top_node = DataTree.root()
    cur_node = node
    while (cur_node is not top_node) and (cur_node is not None):
        categories = NavBarCategory.objects.filter(anchor=cur_node).exclude(anchor__isnull=True)
        if categories.count() > 0:
            if len(section) and categories.count() > 1:
                categories2 = categories.filter(name__icontains=section)
                if categories2.count() > 0:
                    categories = categories2
            return categories[0]
        cur_node = cur_node.parent

    #   Second, see if there's a category with the provided section name.
    categories = NavBarCategory.objects.filter(name=section)
    if categories.count() > 0:
        return categories[0]
    
    #   If all else fails, make something up.
    return NavBarCategory.default()


def qsd_tree_program(qsdTree, node, section, user):
    """
    Obselete, exists temporarily

    This function will go through the tree and add
    appropriate Program-related entries.

    Generators are FUN! (and efficient)
    """
    # useful for copying objects
    import copy

    displayed_programs = {}

    for item in qsdTree:
        entry = item['entry']
        # this entry should obviously be listed
        yield item

        if entry.indent: continue
        if not entry.category.include_auto_links: continue
        
        #   Filter only programs that match the entry's anchor.  This means that within 
        #   each navigation category, you have to pick out the nav bar entries that get
        #   autogenerated links, e.g. "Registration Pages" or "Splash 2008"
        tree_q = QTree(anchor__below=entry.path)
        program_set = Program.objects.filter(tree_q)

        for program in program_set:
            # check to see if we've displayed this program yet.
            if program.id in displayed_programs: continue
            displayed_programs[program.id] = True

            modules = program.getModules(user, section)
            for module in modules:
                navBars = module.getNavBars()
                for navbar_dict in navBars:
                    # make a copy of the default navbar
                    navbar = NavBarEntry(category=entry.category, indent=True)

                    # update the variables in this with that which was given
                    navbar.__dict__.update(navbar_dict)
                    navbar.path = module.program.anchor.parent

                    # send this one along next
                    yield {'entry': navbar, 'has_bits': False}


def makeNavBar(user, node, section='', category=None):
    """ Retrive the appropriate nav bar entries for display based on the provided
    context.  Ideally a category will be provided, which fully determines which
    nav bar entries are shown. """

    return LazyNavBar(user, node, section, category)

@login_required
def updateNavBar(request, section = ''): 
    """
    Update a NavBar entry with the specified data.
    Expects four POST/GET variables:

    navbar_id: The ID of the navbar being modified.
    action:    One of ['up','down','new','delete']
    new_url:   The URL to be redirected to afterwards.
    node_id:   The ID of the datatree you want the path of a new
               navbar to be.

    """

    for i in [ 'navbar_id', 'action', 'new_url', 'node_id' ]:
        assert request.REQUEST.has_key(i), "Need " + str(i)

    action = request.REQUEST['action']

    try:
        if request.REQUEST['node_id'] == '':
            node = None
        else:
            node = DataTree.objects.filter(pk=request.REQUEST['node_id'])[0]
    except Exception:
        # raise Http404
        raise

    try:
        if request.REQUEST['navbar_id'] == '':
            navbar = None
        else:
            navbar = NavBarEntry.objects.filter(pk=request.REQUEST['navbar_id'])[0]
    except Exception:
        #raise Http404
        raise

    assert actions.has_key(action), "Need action"

    if request.REQUEST.has_key('section'):
        section = request.REQUEST['section']

    actions[action](request, navbar, node, section)

    if request.REQUEST['new_url'].strip() == '':
        return HttpResponse('Success')
    
    return HttpResponseRedirect(request.REQUEST['new_url'])

def navBarUp(request, navbar, node, section):
    """ Swap the sort_rank of the specified NavBarEntry and the NavBarEntry immediately before it in the list of NavBarEntrys associated with this tree node, so that this NavBarEntry appears to move up one unit on the page

    Fail silently if this is not possible
    """
    if not UserBit.UserHasPerms(request.user, navbar.path, GetNode("V/Administer/Edit/QSD")):
        raise PermissionDenied, "You don't have permisssion to do that!"

    navbarList = NavBarEntry.objects.filter(path=navbar.path).order_by('sort_rank')

    if not navbar.indent:
        navbarList = navbarList.filter(indent=False)

    last_n = None

    for n in navbarList:
        if navbar == n and last_n != None:
            temp_sort_rank = n.sort_rank
            n.sort_rank = last_n.sort_rank
            last_n.sort_rank = temp_sort_rank

            n.save()
            last_n.save()

        last_n = n
        
    
def navBarDown(request, navbar, node, section):
    """ Swap the sort_rank of the specified NavBarEntry and the NavBarEntry immediately after it in the list of NavBarEntrys associated with this tree node, so that this NavBarEntry appears to move down one unit on the page

    Fail silently if this is not possible
    """
    if not UserBit.UserHasPerms(request.user, navbar.path, GetNode(EDIT_VERB_STRING)):
        raise PermissionDenied, "You don't have permisssion to do that!"

    navbarList = NavBarEntry.objects.filter(path=navbar.path).order_by('sort_rank')

    if not navbar.indent:
        navbarList = navbarList.filter(indent=False)

    last_n = None

    for n in navbarList:
        if last_n != None and navbar == last_n:
            temp_sort_rank = n.sort_rank
            n.sort_rank = last_n.sort_rank
            last_n.sort_rank = temp_sort_rank

            n.save()
            last_n.save()

        last_n = n
        

def navBarNew(request, navbar, node, section):
    """ Create a new NavBarEntry.  Put it at the bottom of the current sort_rank. """
    child_node = request.POST.get('child_node', '')
    if node == '':
        raise ESPError(False), "Please specify a child node."

    try:
        child_node = DataTree.objects.get(id = child_node)
    except DataTree.DoesNotExist:
        raise ESPError(False), "Invalid child node specified."
    
    if not UserBit.UserHasPerms(request.user, node, GetNode(EDIT_VERB_STRING)):
        raise PermissionDenied, "You don't have permisssion to do that!"

    try:
        max_sort_rank = NavBarEntry.objects.filter(path=node).order_by('-sort_rank')[0].sort_rank
    except IndexError:
        max_sort_rank = -100

    new_sort_rank = max_sort_rank + 100

    try:
        url = request.POST['url']

        entry = NavBarEntry()
        entry.path = child_node
        entry.sort_rank = new_sort_rank
        entry.link = url
        entry.text = request.POST['text']
        entry.indent = request.POST['indent']
        entry.section = section

        entry.save()
        
    except Exception:
        raise

    
def navBarDelete(request, navbar, node, section):
    if not UserBit.UserHasPerms(request.user, navbar.path or GetNode('Q'), GetNode(EDIT_VERB_STRING)):
        raise PermissionDenied, "You don't have permission to do that!"

    navbar.delete()


actions = { 'up': navBarUp,
        'down': navBarDown,
        'new': navBarNew,
        'delete': navBarDelete }


