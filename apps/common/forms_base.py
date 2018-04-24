# -*- coding: utf-8 -*-
#
from django import forms


class CombineModelForm(forms.Form):
    form_classes = []

    def __init__(self, *args, **kwargs):
        if not self.form_classes:
            raise ValueError("Must set form_classes attr")
        kwargs.pop('instance', None)
        instances = kwargs.pop('instances', None)
        if not instances:
            instances = [None] * len(self.form_classes)
        super().__init__(*args, **kwargs)
        for cls, instance in zip(self.form_classes, instances):
            name = cls.__name__.lower()
            kwargs['instance'] = instance
            setattr(self, name, cls(*args, **kwargs))
            form = getattr(self, name)
            self.fields.update(form.fields)
            self.initial.update(form.initial)

    def get_form(self, cls):
        name = cls.__name__.lower()
        form = getattr(self, name)
        return form

    def is_valid(self):
        valid = True
        for cls in self.form_classes:
            form = self.get_form(cls)
            if not form.is_valid():
                self.errors.update(form.errors)
                valid = False
        if not super().is_valid():
            valid = False
        return valid

    def clean(self):
        cleaned_data = super().clean()
        for cls in self.form_classes:
            form = self.get_form(cls)
            cleaned_data.update(form.cleaned_data)
        return cleaned_data

    def save(self):
        raise NotImplementedError("Must implement save method")
