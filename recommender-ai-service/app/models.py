from django.db import models

class Recommendation(models.Model):
    customer_id = models.IntegerField()
    book_id = models.IntegerField()
    score = models.FloatField()
    reason = models.CharField(max_length=255, blank=True)
