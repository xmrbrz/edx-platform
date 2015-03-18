""" Views for a student's account information. """

import logging

from django.conf import settings
from django_countries import countries

from django.core.urlresolvers import reverse, resolve
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from dark_lang.models import DarkLangConfig
from edxmako.shortcuts import render_to_response, render_to_string

from student.models import UserProfile
import openedx.core.djangoapps.user_api.preferences.api as perf_api
import openedx.core.djangoapps.user_api.preferences.api as account_api



@login_required
@require_http_methods(['GET'])
def learner_profile(request, username):
    """Render the students profile page.
    Args:
        request (HttpRequest)
    Returns:
        HttpResponse: 200 if the page was sent successfully
        HttpResponse: 302 if not logged in (redirect to login page)
        HttpResponse: 405 if using an unsupported HTTP method
    Example usage:
        GET /account/profile
    """

    released_languages = DarkLangConfig.current().released_languages_list

    # add in the default language if it's not in the list of released languages
    if settings.LANGUAGE_CODE not in released_languages:
        released_languages.append(settings.LANGUAGE_CODE)
        # Re-alphabetize language options
        released_languages.sort()

    language_options = [language for language in settings.LANGUAGES if language[0] in released_languages]

    country_options = [
        (country_code, unicode(country_name))
        for country_code, country_name in sorted(
            countries.countries, key=lambda(__, name): unicode(name)
        )
    ]

    # import pdb; pdb.set_trace()
    # get_user_preferences(request.user, username=username)
    context = {
        'accounts_api_url': reverse("accounts_api", kwargs={'username': username}),
        'preferences_api_url': reverse('preferences_api', kwargs={'username': username}),
        'account_settings_page_url': reverse('account_settings'),
        'info': {
            'show_visibility_select_section': request.user.username == username,
            'country_options': country_options,
            'language_options': language_options
        }
    }
    return render_to_response('student_profile/learner_profile.html', context)