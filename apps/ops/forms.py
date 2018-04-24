from django import forms

from common.forms_base import CombineModelForm
from .models import AuthChangeTask, AuthChangeContent


class AuthChangeTaskForm(forms.ModelForm):
    class Meta:
        model = AuthChangeTask
        exclude = ['id', 'date_created', 'date_updated']


class AuthChangeContentForm(forms.ModelForm):
    class Meta:
        model = AuthChangeContent
        exclude = ['id', 'task', '_password', 'created_by', 'date_created']


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
        content = content_form.save(commit=False)
        content.task = task
        content.save()
        content_form.save_m2m()
        return task



