from django.db import models
from django.contrib.auth.models import User

class Artwork(models.Model):
    # This maps to existing PostgreSQL table
    id = models.IntegerField(primary_key=True)
    label = models.TextField(blank=True, null=True)
    accession_no = models.CharField(max_length=255, blank=True, null=True)
    date = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False # no overwrite of existing table
        db_table = "objects"

class Interaction(models.Model):
    # This is the junction table linking Users to Artworks
    ACTION_CHOICES = [("like", "Like"), ("pass", "Pass")]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "artwork")