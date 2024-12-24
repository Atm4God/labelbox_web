import uuid
from django.db import models
from django.utils import timezone


class TimeStamp(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ('-created_at',)


class AnnotationProject(TimeStamp):
    lb_uid = models.CharField(max_length=200, null=True, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    media_type = models.CharField(
        max_length=50,
        choices=[('IMAGE', 'Image')],
        default='IMAGE'
    )

    def __str__(self):
        return self.name


class AnnotationTask(TimeStamp):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('REVIEWED', 'Reviewed')
    ]

    project = models.ForeignKey(AnnotationProject, on_delete=models.CASCADE, related_name='tasks')
    global_key = models.CharField(max_length=255, unique=True)
    image_url = models.URLField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    annotated_at = models.DateTimeField(null=True, blank=True)

    def mark_as_annotated(self):
        if self.status in ['PENDING', 'IN_PROGRESS']:
            self.status = 'COMPLETED'
            self.annotated_at = timezone.now()
            self.save()
        else:
            raise ValueError("Task cannot be marked as completed from the current status.")

    def __str__(self):
        return f"{self.project.name} - {self.global_key}"


class Annotation(TimeStamp):
    ANNOTATION_TYPES = [
        ('bounding_box', 'Bounding Box'),
        # ('polygon', 'Polygon'),
        # ('point', 'Point'),
        # ('LINE', 'Polyline'),
        # ('MASK', 'Mask'),
        # ('CLASSIFICATION', 'Classification')
    ]

    task = models.ForeignKey(AnnotationTask, on_delete=models.CASCADE, related_name='annotations')
    annotation_type = models.CharField(max_length=20, choices=ANNOTATION_TYPES, default='bounding_box')
    name = models.CharField(max_length=100)  # Tool/classification name
    data = models.JSONField(default=dict, null=True)  # Stores coordinates, values, or other annotation data

    def __str__(self):
        return f"{self.task} - {self.name}"


class Classification(TimeStamp):
    CLASSIFICATION_TYPES = [
        ('RADIO', 'Radio'),
        ('CHECKLIST', 'Checklist'),
        ('TEXT', 'Text')
    ]

    annotation = models.ForeignKey(Annotation, on_delete=models.CASCADE, related_name='classifications')
    name = models.CharField(max_length=100)
    classification_type = models.CharField(max_length=20, choices=CLASSIFICATION_TYPES)
    value = models.JSONField()  # Stores the classification value(s)

    def __str__(self):
        return f"{self.annotation} - {self.name}"


class ExportedAnnotation(TimeStamp):
    task_id = models.CharField(max_length=255)
    annotation_name = models.CharField(max_length=255)
    annotation_type = models.CharField(max_length=50)
    annotation_data = models.JSONField()
    image_file = models.ImageField(upload_to="exported_annotations/")
