from django.contrib.auth.models import User
from django.db import models

class Crop(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='crops'
    )
    crop_name = models.CharField(max_length=255)
    crop_type = models.CharField(max_length=255)
    hectares = models.DecimalField(max_digits=10, decimal_places=2)
    health = models.IntegerField(default=0)
    disease_risk = models.IntegerField(default=0)
    pest_risk = models.IntegerField(default=0)
    status = models.CharField(max_length=100, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.crop_name