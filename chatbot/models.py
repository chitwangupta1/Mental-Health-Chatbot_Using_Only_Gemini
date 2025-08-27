from django.db import models

class Feedback(models.Model):
    question = models.TextField(unique=True)
    response = models.TextField()
    feedback = models.CharField(max_length=10)  # up / down
    model_used = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
