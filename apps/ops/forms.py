import uuid

from django import forms
from django.db import transaction


class SystemUserSettingForm(forms.Form):
    CHANGE_AUTH_INTERVAL = forms.IntegerField(help_text=_("Units: day"), initial=45, required=False, label=_("Interval"))
    CHANGE_PASSWORD = forms.BooleanField(initial=True, required=False, label=_("Change password"))
    CHANGE_SSH_KEY = forms.BooleanField(initial=False, required=False, label=_("Change ssh key"))
    SAME_IN_ALL_ASSET = forms.BooleanField(initial=True, required=False, label=_("Same in all asset"))

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        if instance and instance.cleaned_setting:
            for name, field in self.fields.items():
                field.initial = instance.cleaned_setting.get(name)

    def save(self):
        if not self.instance:
            raise AttributeError("No instance get")

        with transaction.atomic():
            self.instance.cleaned_setting = self.cleaned_data
            self.instance.save()
            return self.instance