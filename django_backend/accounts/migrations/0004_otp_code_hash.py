# Generated manually: add otp_code_hash field for SHA256 OTP storage.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_indonesianaddress_kycverification_registrationevent_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='otp',
            name='otp_code_hash',
            field=models.CharField(blank=True, help_text='SHA256 hash of OTP for secure storage', max_length=64, null=True, verbose_name='Hash OTP'),
        ),
    ]
