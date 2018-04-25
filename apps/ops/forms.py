import uuid

from django import forms
from django.utils.translation import ugettext_lazy as _

from common.forms_base import CombineModelForm
from .models import AuthChangeTask, AuthChangeContent


class AuthChangeTaskForm(forms.ModelForm):
    class Meta:
        model = AuthChangeTask
        exclude = ['id', 'date_created', 'date_updated']
        labels = {
            "different": _("Every asset set a different password")
        }

    def clean_crontab(self):
        interval = self.cleaned_data.get("interval")
        crontab = self.cleaned_data.get("crontab")
        if not interval and not crontab:
            raise forms.ValidationError(_("Interval and crontab must set one"))
        if interval and crontab:
            raise forms.ValidationError(_("Interval and crontab set one only"))
        return crontab


class AuthChangeContentForm(forms.ModelForm):
    class Meta:
        model = AuthChangeContent
        exclude = ['id', 'task', '_password', 'created_by', 'date_created']
        widgets = {
            'assets': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('Asset')}
             ),
            'nodes': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('Node')}
            ),
        }

    def clean_nodes(self):
        assets = self.cleaned_data.get('assets')
        nodes = self.cleaned_data.get("nodes")
        if not assets and not nodes:
            raise forms.ValidationError(_("Asset or node must select one"))
        return nodes


class AuthChangeTaskCreateUpdateForm(CombineModelForm):
    form_classes = [AuthChangeTaskForm, AuthChangeContentForm]

    def __init__(self, *args, **kwargs):
        instances = None
        instance = kwargs.pop('instance')
        if instance:
            content = instance.latest_content
            instances = [instance, content]
        kwargs['instances'] = instances
        super().__init__(*args, **kwargs)

    def save(self):
        task_form = self.get_form(AuthChangeTaskForm)
        content_form = self.get_form(AuthChangeContentForm)
        task = task_form.save()

        content_form.cleaned_data['task'] = task
        if content_form.has_changed():
            content_form.instance.id = str(uuid.uuid4())
        content = content_form.save(commit=False)
        content.task = task
        content.save()
        content_form.save_m2m()
        return task



