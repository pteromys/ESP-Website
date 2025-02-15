from __future__ import absolute_import
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.utils.web import render_to_response
from esp.middleware import ESPError
from esp.users.models import ESPUser
from django.contrib.auth.models import Group
import random
import six
from six.moves import map
from six.moves import range

class BulkCreateAccountModule(ProgramModuleObj):
    doc = """Create a bulk set of accounts (e.g. for outreach)."""

    MAX_PREFIX_LENGTH = 30
    MAX_NUMBER_OF_ACCOUNTS = 1000  # backstop so that an errant request can't fill up the DB with accounts

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Bulk Create Accounts",
            "link_title": "Bulk Create Accounts",
            "module_type": "manage",
            "seq": 10,
            "choosable": 2,
        }

    @main_call
    @needs_admin
    def bulk_create_form(self, request, tl, one, two, module, extra, prog):
        context = {'groups': Group.objects.all().values_list('name', flat=True)}
        return render_to_response(self.baseDir() + 'bulk_create_form.html', request, context)

    @aux_call
    @needs_admin
    def bulk_account_create(self, request, tl, one, two, module, extra, prog):
        row_index = 0
        total_accounts = 0
        prefix_dict = {}
        while 'prefix' + str(1+row_index) in request.POST and 'count' + str(1+row_index) in request.POST:
            row_index += 1
            prefix = request.POST['prefix' + str(row_index)].strip()
            count = request.POST['count' + str(row_index)].strip()
            if prefix == '' and count == '': # skip blank row
                continue

            # validate data
            try:
                count = int(count)
            except ValueError:
                return self.bulk_account_error(request, 'Number of accounts must be a positive integer.')
            if count <= 0:
                return self.bulk_account_error(request, 'Number of accounts must be a positive integer.')
            if prefix == '':
                return self.bulk_account_error(request, 'Prefix cannot be empty.')
            if len(prefix) > self.MAX_PREFIX_LENGTH:
                return self.bulk_account_error(request, 'Prefix cannot be more than %d characters.'
                               % self.MAX_PREFIX_LENGTH)
            total_accounts += count
            if total_accounts > self.MAX_NUMBER_OF_ACCOUNTS:
                return self.bulk_account_error(request, 'Total number of accounts cannot be more than %d.'
                               % self.MAX_NUMBER_OF_ACCOUNTS)
            if prefix in prefix_dict:
                return self.bulk_account_error(request, 'Duplicate prefix: %s' % prefix)

            prefix_dict[prefix] = count

        if not prefix_dict:
            return self.bulk_account_error(request, 'You did not enter any accounts to create.')

        groups = []
        student_or_teacher = False
        for group_string in request.POST.getlist('groups'):
            if group_string in ('Student', 'Teacher'):
                student_or_teacher = True
            group = get_group(group_string)
            if group:
                groups.append(group)
            else:
                return self.bulk_account_error(request, 'There is no group named %s.' % group_string)
        if not student_or_teacher:
            return self.bulk_account_error(request, 'You must select either the Student or Teacher group, '
                            + 'in addition to any other groups you want.')

        result = {}
        # check none of the prefixes have been used before
        used_prefixes = []
        for prefix in prefix_dict:
            if ESPUser.objects.filter(username = prefix + "1").exists():
                used_prefixes.append(prefix)
        if len(used_prefixes) > 2:
            return self.bulk_account_error(request, 'The prefixes ' + ', '.join(used_prefixes[:-1]) + ', and ' + used_prefixes[-1]
                                                    + ' have been used before. Please choose different prefixes.')
        if len(used_prefixes) == 2:
            return self.bulk_account_error(request, 'The prefixes ' + ' and '.join(used_prefixes)
                                                    + ' have been used before. Please choose different prefixes.')
        elif len(used_prefixes) == 1:
            return self.bulk_account_error(request, 'The prefix ' + used_prefixes[0]
                                                    + ' has been used before. Please choose a different prefix.')
        # create users
        for prefix, number in six.iteritems(prefix_dict):
            pw = prefix + str(random.randrange(1000000))
            create_users_for_program(prog, prefix + '{}', pw, groups, number)
            result[prefix] = {'password': pw, 'number': number}
        context = {'passwords': result}

        return render_to_response(self.baseDir() + 'bulk_create_response.html', request, context)

    def bulk_account_error(self, request, message):
        context = {'bulk_account_error_message': message}
        return render_to_response(self.baseDir() + 'bulk_create_error.html', request, context)

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'


def create_users_for_program(program, username_format, password_format, groups, number=1):
    """Create a set of generic users for a program.

    Example use case: create one-time accounts for a HS's outreach students.

    :param program:
        Create a :class:`RegistrationProfile` for the user, with this as
        the value of the `program` field.
    :type program:
        :class:`Program` or None
    :param username_format:
        A format string for the usernames. Must contain exactly one '{}'
        substring. Generate usernames by formatting the string with the
        current index of iteration.
    :type username_format:
        `unicode`
    :param password_format:
        A format string for the password. Generate passwords by formatting
        the string with the current index of iteration. May contain no '{}'
        substrings, to reuse the same password for each user.
    :type password_format:
        `unicode`
    :param groups:
        A list of groups, specified by object or name, to add each new user
        to. Can also pass a single group or group name.
    :type groups:
        (`list` of (:class:`Group` or `unicode`)) or (:class:`Group` or `unicode`)
    :param number:
        A positive number of new users to create.
    :type number:
        `int`
    :return:
        A list of data dictionaries, one for each created user. Each
        dictionary contains 'username', 'password', 'user', and 'profile'
        keys.
    :rtype:
        `list` of `dict`
    """
    if not isinstance(groups, (list, tuple)):
        groups = [groups]
    groups = list(map(get_group, groups))
    ret = []
    for i in range(1, number + 1):
        username = username_format.format(i)
        password = password_format.format(i)
        ret.append(create_user_with_profile(username, password, program, groups))
    return ret


def get_group(group):
    if isinstance(group, Group):
        return group
    elif isinstance(group, six.string_types):
        try:
            return Group.objects.get(name=group)
        except Group.DoesNotExist:
            return None
    else:
        raise ESPError('{} is not a Group or Group name'.format(six.text_type(group)))


def create_user_with_profile(username, password, program, groups):
    # print "creating", username
    user = ESPUser.objects.create_user(username=username, password=password)
    user.groups.add(*groups)
    return {
        'username': username,
        'password': password,
        'user': user,
    }

