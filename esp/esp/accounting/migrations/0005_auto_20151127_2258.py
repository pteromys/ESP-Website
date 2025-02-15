# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0004_remove_account_balance_dec'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transfer',
            name='destination',
            field=models.ForeignKey(related_name='transfer_destination', blank=True, to='accounting.Account', help_text='Destination account; where the money is going to. Leave blank if this is a payment to an outsider.', null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='source',
            field=models.ForeignKey(related_name='transfer_source', blank=True, to='accounting.Account', help_text='Source account; where the money is coming from. Leave blank if this is a payment from outside.', null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='transaction_id',
            field=models.TextField(default='', help_text='If this transfer is from a credit card transaction, stores the transaction ID number from the processor.', max_length=64, verbose_name='Transaction ID', blank=True),
        ),
    ]
