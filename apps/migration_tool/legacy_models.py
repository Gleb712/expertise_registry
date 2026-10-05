# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AppMessages(models.Model):
    msg_date = models.DateTimeField()
    msg_title = models.CharField()
    msg_type = models.CharField()
    msg_text = models.CharField(blank=True, null=True)
    read_by_users = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'app_messages'


class Audit(models.Model):
    uid = models.ForeignKey('Users', models.DO_NOTHING, db_column='uid')
    log_date = models.DateTimeField()
    log = models.CharField()
    exp = models.ForeignKey('Register', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'audit'


class NsiObjects(models.Model):
    value = models.CharField(unique=True)
    is_deleted = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'nsi_objects'


class NsiOpo(models.Model):
    value = models.CharField(unique=True)
    is_deleted = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'nsi_opo'


class Register(models.Model):
    division = models.CharField(blank=True, null=True)
    product_name = models.CharField(blank=True, null=True)
    year_expluatation = models.CharField(blank=True, null=True)
    service_time = models.CharField(blank=True, null=True)
    date_entry_register = models.DateField(blank=True, null=True)
    registration_number = models.CharField(blank=True, null=True)
    conclusion = models.CharField(blank=True, null=True)
    date_expluatation_by = models.DateField(blank=True, null=True)
    is_necessary_expertise_after_delay = models.BooleanField(blank=True, null=True)
    is_necessary_action_after_delay = models.BooleanField(blank=True, null=True)
    is_in_register_opo = models.BooleanField(blank=True, null=True)
    note = models.CharField(blank=True, null=True)
    object = models.ForeignKey(NsiObjects, models.DO_NOTHING, db_column='object', blank=True, null=True)
    opo_number = models.CharField(blank=True, null=True)
    expertise_schedule = models.CharField(blank=True, null=True)
    is_deleted = models.BooleanField()
    is_operational = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'register'


class Scans(models.Model):
    expertise = models.ForeignKey(Register, models.DO_NOTHING)
    path = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'scans'


class UserGroups(models.Model):
    group_name = models.CharField(unique=True)
    access_tags = models.TextField(blank=True, null=True)  # This field type is a guess.
    can_skip_update = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'user_groups'
        # Комментарий убран, он записался в неверной кодировке, можно посмотреть его в бд

class Users(models.Model):
    uid = models.AutoField(primary_key=True)
    name = models.CharField(unique=True)
    last_ip = models.TextField(blank=True, null=True)  # This field type is a guess.
    last_visited = models.DateTimeField(blank=True, null=True)
    full_name = models.CharField(blank=True, null=True)
    group = models.ForeignKey(UserGroups, models.DO_NOTHING, blank=True, null=True)
    is_active = models.BooleanField()
    proff = models.CharField(blank=True, null=True)
    dep = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'users'


class UsersActivity(models.Model):
    user = models.ForeignKey(Users, models.DO_NOTHING)
    log_in_date = models.DateTimeField()
    log_out_date = models.DateTimeField()
    report_count = models.IntegerField()
    exp_cards_count = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'users_activity'
