# -*- coding: utf-8 -*-
#
from django import forms


class SFTPLoginForm(forms.Form):
    host = forms.CharField(max_length=128, required=True)
    port = forms.IntegerField(initial=22, required=True)
    username = forms.CharField(max_length=128, required=True)
    password = forms.CharField(max_length=1024, required=True, widget=forms.PasswordInput)
