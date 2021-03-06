from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template import Context
from django.template.loader import render_to_string


def render_to_string_with_autoescape_off(template_name, dictionary=None,
        context_instance=None):
    dictionary = dictionary or {}
    if not context_instance:
        context_instance = Context(dictionary)
    context_instance.autoescape = False
    return render_to_string(template_name, context_instance=context_instance)


def render_to_email(
    text_template,
    html_template,
    to,
    subject=None,
    subject_template=None,
    context=None,
    send=True,
    opt_out=True
):
    """
    Send a multipart email using the three given templates. Note that to should
    be either User objects or email addresses as strings.

    The context gets augmented with:

     * recipients -- whatever you passed in to (use .is_authenticated() to see
       if it's a User)
     * subject -- whatever was passed or rendered (except for rendering the
       subject)
     * site_name -- the name of the site, according to the django.contrib.sites
       framework
     * domain -- the domain, according to the django.contrib.sites framework
     * protocol -- either "http" or "https" based on settings.SECURE_SSL_REDIRECT

    Note that we aren't using a RequestContext, so context processors won't run.
    Add your stuff in directly using the context parameter.

    subject preferred over subject_template if both are given.
    """

    if context is None:
        context = {}

    def active_user(user_or_email):
        try:
            return user_or_email.is_active
        except AttributeError:
            return False

    if opt_out:
        to = filter(active_user, to)
    if not to:
        return None

    context['recipients'] = to

    def as_email_address(user_or_email):
        try:
            return user_or_email.email
        except AttributeError:
            return user_or_email

    to_addresses = map(as_email_address, to)

    if subject is None:
        subject = render_to_string_with_autoescape_off([subject_template], context).strip()
    context['subject'] = subject

    # Rewrite all recipients to a default recipient in debug mode. Prepends to
    # the subject a debug message indicating original recipients.
    if settings.DEBUG:
        subject = '[DEBUG to:{0}] {1}'.format(','.join(to_addresses), subject)
        to_addresses = settings.DEFAULT_TO_EMAIL

    text = render_to_string_with_autoescape_off([text_template], context)
    html = render_to_string([html_template], context)

    msg = EmailMultiAlternatives(subject, text, to=to_addresses)
    msg.attach_alternative(html, 'text/html')
    if send:
        msg.send()
    return msg
