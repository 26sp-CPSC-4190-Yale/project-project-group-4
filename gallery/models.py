from django.db import models
from django.contrib.auth.models import User


# == Unmanaged models (directly imported from lux.sqlite / not to be modified) ==


class Classifier(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "classifiers"


class Department(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "departments"


class Place(models.Model):
    id = models.IntegerField(primary_key=True)
    label = models.CharField(max_length=255, blank=True, null=True)
    part_of = models.IntegerField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "places"


class Nationality(models.Model):
    id = models.IntegerField(primary_key=True)
    descriptor = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "nationalities"


class Agent(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    begin_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    begin_place = models.ForeignKey(
        Place, on_delete=models.DO_NOTHING,
        blank=True, null=True, related_name="agents_begin",
    )
    end_place = models.ForeignKey(
        Place, on_delete=models.DO_NOTHING,
        blank=True, null=True, related_name="agents_end",
    )
    begin_bce = models.BooleanField(blank=True, null=True)
    end_bce = models.BooleanField(blank=True, null=True)

    nationalities = models.ManyToManyField(
        Nationality, through="AgentNationality",
    )

    class Meta:
        managed = False
        db_table = "agents"


class AgentNationality(models.Model):
    pk = models.CompositePrimaryKey("agent", "nationality")
    agent = models.ForeignKey(
        Agent, on_delete=models.DO_NOTHING, db_column="agt_id",
    )
    nationality = models.ForeignKey(
        Nationality, on_delete=models.DO_NOTHING, db_column="nat_id",
    )

    class Meta:
        managed = False
        db_table = "agents_nationalities"


class Artwork(models.Model):
    id = models.IntegerField(primary_key=True)
    label = models.TextField(blank=True, null=True)
    accession_no = models.CharField(max_length=255, blank=True, null=True)
    date = models.CharField(max_length=255, blank=True, null=True)

    classifiers = models.ManyToManyField(Classifier, through="ObjectClassifier")
    departments = models.ManyToManyField(Department, through="ObjectDepartment")
    places = models.ManyToManyField(Place, through="ObjectPlace")
    agents = models.ManyToManyField(Agent, through="Production")

    class Meta:
        managed = False
        db_table = "objects"


class ObjectClassifier(models.Model):
    pk = models.CompositePrimaryKey("artwork", "classifier")
    artwork = models.ForeignKey(
        Artwork, on_delete=models.DO_NOTHING, db_column="obj_id",
    )
    classifier = models.ForeignKey(
        Classifier, on_delete=models.DO_NOTHING, db_column="cls_id",
    )

    class Meta:
        managed = False
        db_table = "objects_classifiers"


class ObjectDepartment(models.Model):
    pk = models.CompositePrimaryKey("artwork", "department")
    artwork = models.ForeignKey(
        Artwork, on_delete=models.DO_NOTHING, db_column="obj_id",
    )
    department = models.ForeignKey(
        Department, on_delete=models.DO_NOTHING, db_column="dep_id",
    )

    class Meta:
        managed = False
        db_table = "objects_departments"


class ObjectPlace(models.Model):
    pk = models.CompositePrimaryKey("artwork", "place")
    artwork = models.ForeignKey(
        Artwork, on_delete=models.DO_NOTHING, db_column="obj_id",
    )
    place = models.ForeignKey(
        Place, on_delete=models.DO_NOTHING, db_column="pl_id",
    )

    class Meta:
        managed = False
        db_table = "objects_places"


class Production(models.Model):
    pk = models.CompositePrimaryKey("artwork", "agent", "part")
    artwork = models.ForeignKey(
        Artwork, on_delete=models.DO_NOTHING, db_column="obj_id",
    )
    agent = models.ForeignKey(
        Agent, on_delete=models.DO_NOTHING, db_column="agt_id",
    )
    part = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = "productions"


# == Managed models (ours) ==


class Interaction(models.Model):
    ACTION_CHOICES = [("like", "Like"), ("pass", "Pass")]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "artwork")


class TasteSignal(models.Model):
    pk = models.CompositePrimaryKey("user", "facet", "value")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="taste_signals",
    )
    facet = models.CharField(max_length=50)
    value = models.CharField(max_length=255)
    like_count = models.IntegerField(default=0)
    pass_count = models.IntegerField(default=0)
    score = models.FloatField(default=0.5)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["facet", "value"]),
        ]


class Match(models.Model):
    pk = models.CompositePrimaryKey("user1", "user2")
    user1 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="matches_as_user1",
    )
    user2 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="matches_as_user2",
    )
    similarity = models.FloatField()
    matched_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']
