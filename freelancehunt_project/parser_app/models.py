from django.db import models


class Ad(models.Model):
    title = models.CharField(null=True, blank=True, max_length=255)
    budget = models.CharField(null=True, blank=True, max_length=255)
    employer = models.CharField(null=True, blank=True, max_length=255)
    description = models.TextField(null=True, blank=True)
    url = models.URLField(unique=True)
    categories = models.CharField(null=True, blank=True, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

