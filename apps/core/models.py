import json
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SystemSetting(models.Model):
    class ValueType(models.TextChoices):
        STRING = 'string', 'String'
        INT = 'int', 'Integer'
        FLOAT = 'float', 'Float'
        BOOL = 'bool', 'Boolean'
        JSON = 'json', 'JSON'

    key = models.CharField(max_length=255, unique=True)
    value = models.TextField()
    value_type = models.CharField(max_length=10, choices=ValueType.choices, default=ValueType.STRING)
    description = models.TextField(blank=True)
    is_secret = models.BooleanField(default=False)

    def get_value(self):
        if self.value_type == self.ValueType.INT:
            return int(self.value)
        elif self.value_type == self.ValueType.FLOAT:
            return float(self.value)
        elif self.value_type == self.ValueType.BOOL:
            return self.value.lower() in ('true', '1', 'yes')
        elif self.value_type == self.ValueType.JSON:
            return json.loads(self.value)
        return self.value

    def __str__(self):
        return self.key
