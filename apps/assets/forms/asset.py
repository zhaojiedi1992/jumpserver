# -*- coding: utf-8 -*-
#
from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import Asset, AdminUser, AssetAuthBook
from common.utils import get_logger

logger = get_logger(__file__)
__all__ = ['AssetCreateUpdateForm', 'AssetBulkUpdateForm']


class AssetCreateUpdateForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput, max_length=128,
        strip=True, required=False,
        help_text=_('If password different with this admin user, set it'),
        label=_("Password individual"),
    )

    class Meta:
        model = Asset
        fields = [
            'hostname', 'ip', 'public_ip', 'port',  'comment',
            'nodes', 'is_active', 'admin_user', 'labels', 'platform',
            'domain', 'number'

        ]
        widgets = {
            'nodes': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Nodes')
            }),
            'admin_user': forms.Select(attrs={
                'class': 'select2', 'data-placeholder': _('Admin user')
            }),
            'labels': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Label')
            }),
            'port': forms.TextInput(),
            'domain': forms.Select(attrs={
                'class': 'select2', 'data-placeholder': _('Domain')
            }),
        }
        labels = {
            'nodes': _("Node"),
        }
        help_texts = {
            'hostname': '* required',
            'ip': '* required',
            'port': '* required',
            'admin_user': _('root, Administrator or other manage privilege user existed in asset'),
            'platform': _("* required Must set exact system platform, Windows, Linux ..."),
            'domain': _("If your have some network not connect with each other, you can set domain")
        }

    def save(self, *args, **kwargs):
        password = self.cleaned_data.pop('password')
        admin_user = self.cleaned_data.get('admin_user')
        instance = super().save(*args, **kwargs)
        if password and admin_user:
            auth = AssetAuthBook.objects.create(
                asset=instance, username=admin_user.username
            )
            auth.password = password
            auth.save()
        return instance


class AssetBulkUpdateForm(forms.ModelForm):
    assets = forms.ModelMultipleChoiceField(
        required=True, help_text='* required',
        label=_('Select assets'), queryset=Asset.objects.all(),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'select2',
                'data-placeholder': _('Select assets')
            }
        )
    )
    port = forms.IntegerField(
        label=_('Port'), required=False, min_value=1, max_value=65535,
    )
    admin_user = forms.ModelChoiceField(
        required=False, queryset=AdminUser.objects.all(),
        label=_("Admin user"),
        widget=forms.Select(
            attrs={
                'class': 'select2',
                'data-placeholder': _('Admin user')
            }
        )
    )

    class Meta:
        model = Asset
        fields = [
            'assets', 'port',  'admin_user', 'labels', 'nodes', 'platform'
        ]
        widgets = {
            'labels': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('Label')}
            ),
            'nodes': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('Node')}
            ),
        }

    def save(self, commit=True):
        changed_fields = []
        for field in self._meta.fields:
            if self.data.get(field) not in [None, '']:
                changed_fields.append(field)

        cleaned_data = {k: v for k, v in self.cleaned_data.items()
                        if k in changed_fields}
        assets = cleaned_data.pop('assets')
        labels = cleaned_data.pop('labels', [])
        nodes = cleaned_data.pop('nodes')
        assets = Asset.objects.filter(id__in=[asset.id for asset in assets])
        assets.update(**cleaned_data)

        if labels:
            for label in labels:
                label.assets.add(*tuple(assets))
        if nodes:
            for node in nodes:
                node.assets.add(*tuple(assets))
        return assets
