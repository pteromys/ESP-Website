
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
from esp.qsd.models import QuasiStaticData
from esp.qsd.forms import QSDEditForm
from django.contrib.auth.models import User
from esp.users.models import ContactInfo, UserBit, GetNodeOrNoBits
from esp.datatree.models import *
from esp.web.views.navBar import makeNavBar
from esp.web.models import NavBarEntry, NavBarCategory
from esp.web.util.main import render_to_response
from django.http import HttpResponse, Http404, HttpResponseNotAllowed
from esp.qsdmedia.models import Media
from esp.lib.markdownaddons import ESPMarkdown
from os.path import basename, dirname
from datetime import datetime
from django.core.cache import cache
from django.template.defaultfilters import urlencode
from esp.datatree.decorators import branch_find
from esp.middleware import ESPError, Http403
from esp.utils.no_autocookie import disable_csrf_cookie_update
from django.utils.cache import add_never_cache_headers, patch_cache_control, patch_vary_headers
from django.views.decorators.vary import vary_on_cookie
from django.views.decorators.cache import cache_control
from esp.cache.varnish import purge_page
import urllib
import reversion

# default edit permission
EDIT_PERM = 'V/Administer/Edit'

# spacing between separate nav bar entries
DEFAULT_SPACING = 5

def handle_ajax_mover(method):
    """
    Takes a view and wraps it in such a way that a user can
    submit AJAX requests for changing the order of navbar entries.
    """

    def ajax_mover(request, *args, **kwargs):
        if not request.GET.has_key('ajax_movepage') or \
           not request.GET.has_key('seq'):
            return method(request, *args, **kwargs)

        START = 'nav_entry__'

        entries = request.GET['seq'].strip(',').split(',')
        try:
            entries = [x[len(START):] for x in entries]
        except:
            return method(request, *args, **kwargs)

        # using some good magic we get a list of tree_node common
        # ancestors
        tree_nodes = DataTree.get_only_parents(DataTree.objects.filter(navbar__in = entries))

        edit_verb = GetNode(EDIT_PERM)
        for node in tree_nodes:
            if not UserBit.UserHasPerms(request.user,
                            node,
                            edit_verb):
                return method(request, *args, **kwargs)

        # now we've properly assessed the person knows what
        # they're doing. We actually do the stuff we wanted.
        rank = 0
        for entry in entries:
            try:
                navbar = NavBarEntry.objects.get(pk = entry)
                navbar.sort_rank = rank
                navbar.save()
                rank += DEFAULT_SPACING
            except:
                pass

        return HttpResponse('Success')

    return ajax_mover



@handle_ajax_mover
@branch_find
#@vary_on_cookie
#@cache_control(max_age=180)    NOTE: patch_cache_control() below inserts cache header for view mode only
@disable_csrf_cookie_update
def qsd(request, branch, name, section, action):

    READ_VERB = 'V/Flags/Public'
    EDIT_VERB = 'V/Administer/Edit/QSD'

    if action == 'read':
        base_url = request.path[:-5]
    else:
        base_url = request.path[:(-len(action)-6)]

    # Detect edit authorizations
    have_read = True
    
    if not have_read and action == 'read':
        raise Http403, "You do not have permission to access this page."

    # Fetch the QSD object
    try:
        qsd_rec = QuasiStaticData.objects.get_by_path__name(branch, name)
        if qsd_rec == None:
            raise QuasiStaticData.DoesNotExist
        if qsd_rec.disabled:
            raise QuasiStaticData.DoesNotExist

    except QuasiStaticData.DoesNotExist:
        have_edit = UserBit.UserHasPerms(request.user, branch, EDIT_VERB)

        if have_edit:
            if action in ('edit','create',):
                qsd_rec = QuasiStaticData()
                qsd_rec.path = branch
                qsd_rec.name = name
                qsd_rec.nav_category = NavBarCategory.default()
                qsd_rec.title = 'New Page'
                qsd_rec.content = 'Please insert your text here'
                qsd_rec.create_date = datetime.now()
                qsd_rec.keywords = ''
                qsd_rec.description = ''
                action = 'edit'

            if (action == 'read'):
                edit_link = base_url+'.edit.html'
                return render_to_response('qsd/nopage_edit.html', request, (branch, section), {'edit_link': edit_link}, use_request_context=False)
        else:
            if action == 'read':
                raise Http404, 'This page does not exist.'
            else:
                raise Http403, 'Sorry, you can not modify <tt>%s</tt>.' % request.path

    if action == 'create':
        action = 'edit'

    # Detect the standard read verb
    if action == 'read':        
        if not have_read:
            raise Http403, 'You do not have permission to read this page.'

        # Render response
        response = render_to_response('qsd/qsd.html', request, (branch, section), {
            'title': qsd_rec.title,
            'nav_category': qsd_rec.nav_category, 
            'content': qsd_rec.html(),
            'qsdrec': qsd_rec,
            'have_edit': True,  ## Edit-ness is determined client-side these days
            'edit_url': base_url + ".edit.html" }, use_request_context=False)

#        patch_vary_headers(response, ['Cookie'])
#        if have_edit:
#            add_never_cache_headers(response)
#            patch_cache_control(response, no_cache=True, no_store=True)
#        else:
        patch_cache_control(response, max_age=3600, public=True)

        return response

            
    # Detect POST
    if request.POST.has_key('post_edit'):
        have_edit = UserBit.UserHasPerms(request.user, branch, EDIT_VERB)

        if not have_edit:
            raise Http403, "Sorry, you do not have permission to edit this page."
        
        # Arguably, this should retrieve the DB object, use the .copy()
        # method, and then update it. Doing it this way saves a DB call
        # (and requires me to make fewer changes).
        qsd_rec_new = QuasiStaticData()
        qsd_rec_new.path = branch
        qsd_rec_new.name = name
        qsd_rec_new.author = request.user
        qsd_rec_new.nav_category = NavBarCategory.objects.get(id=request.POST['nav_category'])
        qsd_rec_new.content = request.POST['content']
        qsd_rec_new.title = request.POST['title']
        qsd_rec_new.description = request.POST['description']
        qsd_rec_new.keywords    = request.POST['keywords']
        qsd_rec_new.save()

        # We should also purge the cache
        purge_page(qsd_rec_new.url())

        qsd_rec = qsd_rec_new

        # If any files were uploaded, save them
        for name, file in request.FILES.iteritems():
            m = Media()

            # Strip "media/" from FILE, and strip the file name; just return the path
            path = dirname(name[9:])
            if path == '':
                m.anchor = qsd_rec.path
            else:
                m.anchor = GetNode('Q/' + dirname(name))
                
            # Do we want a better/manual mechanism for setting friendly_name?
            m.friendly_name = basename(name)
            
            m.format = ''

            local_filename = name
            if name[:9] == 'qsdmedia/':
                local_filename = name[9:]
                    
            m.handle_file(file, local_filename)
            m.save()


    # Detect the edit verb
    if action == 'edit':
        have_edit = UserBit.UserHasPerms(request.user, branch, EDIT_VERB)

        # Enforce authorizations (FIXME: SHOW A REAL ERROR!)
        if not have_edit:
            raise ESPError(False), "You don't have permission to edit this page."

        m = ESPMarkdown(qsd_rec.content, media={})

        m.toString()
#        assert False, m.BrokenLinks()
        
        # Render an edit form
        return render_to_response('qsd/qsd_edit.html', request, (branch, section), {
            'title'        : qsd_rec.title,
            'content'      : qsd_rec.content,
            'keywords'     : qsd_rec.keywords,
            'description'  : qsd_rec.description,
            'nav_category' : qsd_rec.nav_category, 
            'nav_categories': NavBarCategory.objects.all(),
            'qsdrec'       : qsd_rec,
            'qsd'          : True,
            'missing_files': m.BrokenLinks(),
            'target_url'   : base_url.split("/")[-1] + ".edit.html",
            'return_to_view': base_url.split("/")[-1] + ".html?v=" + str(qsd_rec.id) }, # pass a "unique" query parameter to bypass browser cache
                                  use_request_context=False)

    
    # Operation Complete!
    raise Http404('Unexpected QSD operation')

def ajax_qsd(request):
    """ Ajax function for in-line QSD editing.  """
    from django.utils import simplejson
    from esp.lib.templatetags.markdown import markdown

    EDIT_VERB = 'V/Administer/Edit/QSD'

    result = {}
    post_dict = request.POST.copy()

    if ( request.user.id is None ):
        return HttpResponse(content='Oops! Your session expired!\nPlease open another window, log in, and try again.\nYour changes will not be lost if you keep this page open.', status=500)
    if post_dict['cmd'] == "update":
        qsdold = QuasiStaticData.objects.get(id=post_dict['id'])
        if not UserBit.UserHasPerms(request.user, qsdold.path, EDIT_VERB):
            return HttpResponse(content='Sorry, you do not have permission to edit this page.', status=500)
        qsd = qsdold.copy()
        qsd.content = post_dict['data']
        qsd.load_cur_user_time(request, )
        # Local change here, to enable QSD editing.
        qsd.save()
        result['status'] = 1
        result['content'] = markdown(qsd.content)
        result['id'] = qsd.id
    if post_dict['cmd'] == "create":
        qsd_path = DataTree.objects.get(id=post_dict['anchor'])
        if not UserBit.UserHasPerms(request.user, qsd_path, EDIT_VERB):
            return HttpResponse(content="Sorry, you do not have permission to edit this page.", status=500)
        qsd, created = QuasiStaticData.objects.get_or_create(name=post_dict['name'],path=qsd_path,defaults={'author': request.user})
        qsd.content = post_dict['data']
        qsd.author = request.user
        qsd.save()
        result['status'] = 1
        result['content'] = markdown(qsd.content)
        result['id'] = qsd.id
    
    return HttpResponse(simplejson.dumps(result))

def qsd_fragment(request, cmd):
    """QSD requests that return fragments"""
    from django.utils import simplejson
    from django.conf import settings
    import pytz

    def can_edit(user, tree_uri):
        # I chose to make this inefficient rather than create a slew of datatree nodes
        VERB = 'V/Administer/Edit/QSD'
        if UserBit.UserHasPerms(user, tree_uri, VERB):
            return True
        while DataTree.DELIMITER in tree_uri:
            tree_uri = tree_uri.rsplit(DataTree.DELIMITER, 1)[0]
            if UserBit.UserHasPerms(user, tree_uri, VERB, recursive_required = True):
                return True
        return False

    def get_url_parts(url):
        # I really hope I don't have to maintain this.
        from esp.section_data import section_redirect_keys, section_prefix_keys
        # Preprocess the URL: strip spaces and leading slash
        url = url.strip()
        if url[0] == '/':
            url = url[1:]
        # Extract subsection
        parts = url.split('/')
        if parts[0] in section_redirect_keys:
            subsection = parts.pop(0)
        else:
            subsection = None
        # Find a DataTree node
        parts[:0] = ['Q', section_redirect_keys[subsection]]
        view_address = parts.pop()[:-5] # assumes ".html" ending
        if not view_address.strip():
            return None  #empty final component is invalid
        tree_uri = DataTree.DELIMITER.join(parts)
        # Tag the view address with a subsection prefix
        if section_prefix_keys.has_key(subsection):
            subsection = section_prefix_keys[subsection]
        if subsection:
            view_address = '%s:%s' % (subsection, view_address)
        # Finally, return. Phew!
        return (tree_uri, view_address)

    def get_by_url(url):
        try:
            tree_uri, view_address = get_url_parts(url)
            return QuasiStaticData.objects.get_by_path__name(DataTree.get_by_uri(tree_uri), view_address)
        except (DataTree.DoesNotExist, QuasiStaticData.DoesNotExist):
            return None

    def check_perms(user, url):
        if user.id is None:
            return (undefined_user_message(), None, None)
        tree_uri, view_address = get_url_parts(url)
        if not can_edit(user, tree_uri):
            return (permission_denied_message(), tree_uri, view_address)
        return (None, tree_uri, view_address)

    def last_revision_string(q):
        if q.id is None:
            return ''
        ans = reversion.get_for_object(q).order_by('-revision__date_created')
        if ans:
            return ans[0].revision.date_created.isoformat()

    permission_denied_message = lambda: HttpResponse(content='You don\'t have permission to edit this page.', status=403)
    undefined_user_message = lambda: HttpResponse(content='Oops! Your session expired!\nPlease open another window, log in, and try again.\nYour changes will not be lost if you keep this page open.', status=403)
    not_found_message = lambda: HttpResponse(content='No QSD found at %s' % url, status=404)


    url = request.POST.get('url', request.GET.get('url'))
    if url is None:
        return HttpResponse(content='What URL?', status=404)
    # Knock off everything but the path name, just in case JS passed us something silly.
    url = urllib.splithost(urllib.splittype(url)[1])[1]

    if cmd == 'write':
        msg, tree_uri, view_address = check_perms(request.user, url)
        if msg:
            return msg
        anchor = GetNode(tree_uri)
        q = QuasiStaticData.objects.get_by_path__name(anchor, view_address) or QuasiStaticData()
        if last_revision_string(q) != request.POST['last_revision_string']:
            return HttpResponse(content="Edit conflict! The page has been rewritten since you opened it.", status=409)
        q.path = anchor
        q.name = view_address
        q.author = request.user
        q.create_date = datetime.now()
        with reversion.create_revision():
            q = QSDEditForm(request.POST, instance=q).save()
        # We should also purge the cache
        purge_page(q.url())
        # Return updated HTML
        cmd = 'html'
        url = q.url()
    if cmd == 'delete':
        msg, tree_uri, view_address = check_perms(request.user, url)
        if msg:
            return msg
        q = get_by_url(url)
        if q:
            #with reversion.create_revision():
            #    q.delete()
            return HttpResponse(content='Deleted %s' % url)
        else:
            return not_found_message()
    if cmd == 'form':
        msg, tree_uri, view_address = check_perms(request.user, url)
        if msg:
            return msg
        basename = url.rsplit('/', 1)[-1].split('.', 1)[0]
        q = get_by_url(url) or QuasiStaticData()
        f = QSDEditForm(instance=q, auto_id='id_%%s_%s' % basename, label_suffix='',
            initial={'url': url, 'last_revision_string': last_revision_string(q)})
        return render_to_response('qsd/qsd_form_fragment.html', {'form': f})
    if cmd == 'html':
        q = get_by_url(url)
        if q:
            return HttpResponse(content=q.html())
        else:
            return not_found_message()
    if cmd == 'diff':
        pass # Not Implemented

    return HttpResponse('No such command.', status=404) #400?

