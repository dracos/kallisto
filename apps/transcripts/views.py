from django import forms
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, UpdateView
from .models import Mission, Page, Revision, LockExpired


class CleanNext(DetailView):
    model = Mission
    slug_field = 'short_name'
    
    def get(self, request, *args, **kwargs):
        mission = self.get_object()
        page = mission.next_page_for_user(request.user)
        if page is None:
            return HttpResponseRedirect(reverse('homepage'))
        else:
            return HttpResponseRedirect(
                reverse(
                    'mission-page',
                    kwargs={
                        'slug': mission.short_name,
                        'page': page.number,
                    }
                )
            )
clean = login_required(CleanNext.as_view())


class CleanPage(UpdateView):
    model = Page
    template_name_suffix = '_clean'

    def get_initial(self):
        return {
            'text': self.object.text,
        }
    
    def get_form_class(self):
        obj = self.object
        user = self.request.user

        class MakeRevision(forms.Form):
            text = forms.CharField(
                label=_(u'Cleaned page'),
                widget=forms.Textarea(
                    attrs={
                        'cols': 100,
                        'rows': 35
                    },
                ),
            )

            def save(self):
                obj.create_revision(
                    self.cleaned_data['text'],
                    user,
                )
                return obj

        return MakeRevision

    def get_form_kwargs(self):
        kwargs = super(CleanPage, self).get_form_kwargs()
        del kwargs['instance']
        return kwargs

    def get_context_data(self, **kwargs):
        return super(CleanPage, self).get_context_data(**kwargs)
    
    def get_object(self, queryset=None):
        try:
            mission = Mission.objects.get(short_name=self.kwargs.get('slug'))
        except Mission.DoesNotExist:
            raise Http404

        try:
            page = mission.pages.get(number=int(self.kwargs.get('page')))
        except Page.DoesNotExist:
            raise Http404
        except ValueError:
            # could not convert number URL kwarg to int
            raise Http404

        return page

    def form_valid(self, form):
        try:
            form.save()
            return HttpResponseRedirect(self.get_success_url())
        except LockExpired:
            form.add_error(
                None,
                forms.ValidationError(
                    _(
                        u"Lock expired; please go back to "
                        u"the home page to continue cleaning."
                    )
                ),
            )
            return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse(
            'mission-clean-next',
            kwargs={
                'slug': self.object.mission.short_name,
            },
        )

page = login_required(CleanPage.as_view())
