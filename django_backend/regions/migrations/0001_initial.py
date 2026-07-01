from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Province',
            fields=[
                ('code', models.CharField(max_length=2, primary_key=True, serialize=False, validators=[django.core.validators.MinLengthValidator(2)], verbose_name='Kode Kemendagri')),
                ('name', models.CharField(max_length=100, verbose_name='Nama Provinsi')),
                ('name_upper', models.CharField(db_index=True, max_length=100, verbose_name='Nama (UPPER)')),
                ('latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Provinsi',
                'verbose_name_plural': 'Provinsi',
                'db_table': 'regions_province',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Regency',
            fields=[
                ('code', models.CharField(max_length=4, primary_key=True, serialize=False, validators=[django.core.validators.MinLengthValidator(4)], verbose_name='Kode Kemendagri')),
                ('name', models.CharField(max_length=100, verbose_name='Nama Kabupaten/Kota')),
                ('name_upper', models.CharField(db_index=True, max_length=100, verbose_name='Nama (UPPER)')),
                ('type', models.CharField(choices=[('kabupaten', 'Kabupaten'), ('kota', 'Kota')], default='kabupaten', max_length=20)),
                ('latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('province', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='regencies', to='regions.province')),
            ],
            options={
                'verbose_name': 'Kabupaten/Kota',
                'verbose_name_plural': 'Kabupaten/Kota',
                'db_table': 'regions_regency',
                'ordering': ['name'],
            },
        ),
        migrations.AddIndex(
            model_name='regency',
            index=models.Index(fields=['province', 'name'], name='regions_reg_provinc_1b50cc_idx'),
        ),
        migrations.CreateModel(
            name='District',
            fields=[
                ('code', models.CharField(max_length=6, primary_key=True, serialize=False, validators=[django.core.validators.MinLengthValidator(6)], verbose_name='Kode Kemendagri')),
                ('name', models.CharField(max_length=100, verbose_name='Nama Kecamatan')),
                ('name_upper', models.CharField(db_index=True, max_length=100, verbose_name='Nama (UPPER)')),
                ('latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('regency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='districts', to='regions.regency')),
                ('province', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='districts', to='regions.province')),
            ],
            options={
                'verbose_name': 'Kecamatan',
                'verbose_name_plural': 'Kecamatan',
                'db_table': 'regions_district',
                'ordering': ['name'],
            },
        ),
        migrations.AddIndex(
            model_name='district',
            index=models.Index(fields=['regency', 'name'], name='regions_dis_regency_6e5e4f_idx'),
        ),
        migrations.AddIndex(
            model_name='district',
            index=models.Index(fields=['province', 'name'], name='regions_dis_provinc_3b48ed_idx'),
        ),
        migrations.CreateModel(
            name='Village',
            fields=[
                ('code', models.CharField(max_length=10, primary_key=True, serialize=False, validators=[django.core.validators.MinLengthValidator(10)], verbose_name='Kode BPS')),
                ('name', models.CharField(max_length=100, verbose_name='Nama Desa/Kelurahan')),
                ('name_upper', models.CharField(db_index=True, max_length=100, verbose_name='Nama (UPPER)')),
                ('type', models.CharField(choices=[('desa', 'Desa'), ('kelurahan', 'Kelurahan')], default='desa', max_length=20)),
                ('postal_code', models.CharField(blank=True, max_length=5, verbose_name='Kode Pos')),
                ('latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('district', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='villages', to='regions.district')),
                ('regency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='villages', to='regions.regency')),
                ('province', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='villages', to='regions.province')),
            ],
            options={
                'verbose_name': 'Desa/Kelurahan',
                'verbose_name_plural': 'Desa/Kelurahan',
                'db_table': 'regions_village',
                'ordering': ['name'],
            },
        ),
        migrations.AddIndex(
            model_name='village',
            index=models.Index(fields=['district', 'name'], name='regions_vil_distric_8fa806_idx'),
        ),
        migrations.AddIndex(
            model_name='village',
            index=models.Index(fields=['postal_code'], name='regions_vil_postal_abdef0_idx'),
        ),
        migrations.AddIndex(
            model_name='village',
            index=models.Index(fields=['name_upper'], name='regions_vil_name_up_0142a6_idx'),
        ),
    ]
