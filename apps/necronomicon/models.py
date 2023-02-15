import typing

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import DatabaseError, models, transaction
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django_celery_results.models import TaskResult
from rest_framework.serializers import ModelSerializer

from . import tasks


class BatchStatus(models.TextChoices):
    INITIAL = 'initial', _("Initial")
    PREPARING = 'preparing', _("Preparing Stats")
    PREPARED = 'prepared', _("Stats Prepared")
    DELETE = 'delete', _("Deleting")
    DELETED = 'deleted', _("Deleted")


class Batch(models.Model):
    """Transaction unit -> all changes are done here or none"""

    created = models.DateTimeField(default=now)
    status = models.CharField(
        max_length=20, choices=BatchStatus.choices, default=BatchStatus.INITIAL
    )
    task_result_id = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name_plural = _("Batches")

    @property
    def task_result(self) -> typing.Optional[TaskResult]:
        try:
            return TaskResult.objects.get(pk=self.task_result_id)
        except TaskResult.DoesNotExist:
            return None

    @property
    def can_delete(self):
        return self.status == BatchStatus.PREPARED

    @property
    def can_prepare(self):
        return self.status == BatchStatus.INITIAL

    @cached_property
    def info(self):
        return [e.info for e in self.candidates.all()]

    def plan_delete_batch_targets(self) -> bool:

        with transaction.atomic():
            # lock
            try:
                Batch.objects.filter(pk=self.pk).select_for_update()
            except DatabaseError:
                # abort -> something is already running
                return False

            if not self.can_delete:
                return False

            self.status = BatchStatus.DELETE
            self.task_result_id = None
            self.save()
            transaction.on_commit(lambda: tasks.delete_batch_targets.delay(self.pk))

        return True

    def delete_batch_targets(
        self, task_result: typing.Optional[TaskResult]
    ) -> typing.Optional[int]:
        # Should be run by a celery task

        with transaction.atomic():
            # lock
            try:
                Batch.objects.filter(pk=self.pk).select_for_update()
            except DatabaseError:
                # abort -> something is already running
                return None

            if self.status != BatchStatus.DELETE:
                return None

            count = 0
            for candidate in self.candidates.all():
                if candidate.content_object:
                    candidate.delete_object()
                    count += 1
            self.status = BatchStatus.DELETED
            self.task_result_id = task_result and task_result.pk
            self.save()

        return count

    def prepare_batch(self, task_result: typing.Optional[TaskResult]) -> typing.Optional[int]:
        # Should be run by a celery task

        with transaction.atomic():
            # lock
            try:
                Batch.objects.filter(pk=self.pk).select_for_update()
            except DatabaseError:
                # abort -> something is already running
                return None

            if self.status != BatchStatus.PREPARING:
                return None

            count = 0
            for candidate in self.candidates.all():
                if candidate.content_object:
                    candidate.update_info()
                    count += 1

            self.status = BatchStatus.PREPARED
            self.task_result_id = task_result and task_result.pk
            self.save()

            return count

    def plan_prepare_batch(self) -> bool:

        with transaction.atomic():
            # lock
            try:
                Batch.objects.filter(pk=self.pk).select_for_update()
            except DatabaseError:
                # abort -> something is already running
                return False

            if not self.can_prepare:
                return False

            self.status = BatchStatus.PREPARING
            self.task_result_id = None
            self.save()
            transaction.on_commit(lambda: tasks.prepare_batch.delay(self.pk))

        return True

    def __str__(self):
        for candidate in self.candidates.all():
            return (
                f"{candidate.content_type.app_label}.{candidate.content_type.model}({self.created})"
            )
        return "<MISSING CANDIDATE>"

    @classmethod
    def create_from_queryset(cls, queryset) -> typing.Optional['Batch']:
        if queryset.exists():
            batch = Batch.objects.create()
            for obj in queryset:
                Candidate.objects.create(batch=batch, content_object=obj)
            return batch

        return None


class Candidate(models.Model):
    batch = models.ForeignKey(Batch, related_name="candidates", on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey(ct_field='content_type', fk_field='object_id')

    info = models.JSONField(default=dict, blank=True, null=True)

    def serialized_object(self) -> typing.Optional[dict]:
        if not self.content_object:
            return None

        class Serializer(ModelSerializer):
            class Meta:
                model = self.content_type.model_class()
                fields = "__all__"

        return Serializer(self.content_object).data

    def update_info(self):
        model_class = self.content_type.model_class()
        if self.content_object:
            try:
                with transaction.atomic():
                    stats = model_class.objects.filter(pk=self.object_id).delete()
                    # We need only to collect stats therefore the transaction is aborted
                    raise RuntimeError("Abort")
            except RuntimeError:
                pass

            Candidate.objects.filter(pk=self.pk).update(
                info={"object": self.serialized_object(), "stats": stats}
            )

    def delete_object(self):
        model_class = self.content_type.model_class()
        if self.content_object:
            Candidate.objects.filter(pk=self.pk).update(
                info={
                    "object": self.serialized_object(),
                    "stats": model_class.objects.filter(pk=self.object_id).delete(),
                }
            )

    def __str__(self):
        return f"{self.content_type.app_label}.{self.content_type.model}({self.object_id})"

    def save(self, *args, **kwargs):
        # Update info related to the object
        self.info = {
            "object": self.serialized_object() or (self.info or {}).get("object", {}),
            "stats": (self.info or {}).get("stats", {}),
        }
        return super().save(*args, **kwargs)

    class Meta:
        indexes = (models.Index(fields=["content_type", "object_id"], name="content_index"),)
