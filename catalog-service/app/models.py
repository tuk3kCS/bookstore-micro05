from django.db import models

class Catalog(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
