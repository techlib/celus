from datetime import timedelta

from django.db.models import F, Max

from core.logic.dates import month_start, month_end


def split_fetch_intentions(accesslog_model, fetchintention_model):
    max_queue_id = fetchintention_model.objects.all().aggregate(Max('queue_id'))['queue_id__max']
    queue_id_remap = {}
    previous_id_remap = {}
    # when duplicate_of_id cannot be resolved immediately because the duplicated fi has not been
    # seen yet
    delayed_duplicates = {}

    for fi in (
        fetchintention_model.objects.exclude(
            start_date__month=F('end_date__month'), start_date__year=F('end_date__year')
        )
        .order_by('pk')
        .select_for_update()
    ):
        # ordering by pk should ensure that we do not catch reference to pk in previous_intentions
        # before seeing that intention
        end_month = month_start(fi.end_date)
        current_month = fi.start_date
        # we modify the fi in place and then use it as a template for cloning other intentions
        fi.end_date = month_end(current_month)
        fi.save()
        fa = fi.attempt
        original_ib_pk = None
        if fa:
            fa.end_date = fi.end_date
            fa.save()
            original_ib_pk = fa.import_batch_id
        orig_queue_id = fi.queue_id
        orig_fi_pk = fi.pk
        orig_previous_intention_id = fi.previous_intention_id
        orig_duplicate_of_id = fi.duplicate_of_id
        while current_month < end_month:
            # duplicate the FetchIntention
            current_month = month_start(current_month + timedelta(days=40))
            fi.id = None  # we ensure creation of a new intention object
            fi.start_date = current_month
            fi.end_date = month_end(current_month)
            # check if we have already remapped the queue ID or not
            queue_key = (orig_queue_id, current_month)
            if queue_key in queue_id_remap:
                fi.queue_id = queue_id_remap[queue_key]
            else:
                max_queue_id += 1
                fi.queue_id = max_queue_id
                queue_id_remap[queue_key] = fi.queue_id
            # similar check for previous intention
            if orig_previous_intention_id:
                # this must be successful (hopefully)
                fi.previous_intention_id = previous_id_remap[
                    (orig_previous_intention_id, current_month)
                ]
            # and duplicate of
            delay_dup = False
            if orig_duplicate_of_id:
                # this must be successful (hopefully)
                dup_key = (orig_duplicate_of_id, current_month)
                if dup_key in previous_id_remap:
                    fi.duplicate_of_id = previous_id_remap[dup_key]
                else:
                    # we cannot resolve this yet, so we have to delay it
                    fi.duplicate_of_id = None
                    delay_dup = True
            if fa:
                # duplicate the FetchAttempt
                fa.id = None
                fa.start_date = fi.start_date
                fa.end_date = fi.end_date
                if fa.import_batch:
                    # duplicate ImportBatch
                    ib = fa.import_batch
                    ib.id = None
                    ib.save()
                    # update accesslogs
                    accesslog_model.objects.filter(
                        import_batch_id=original_ib_pk, date=current_month
                    ).update(import_batch_id=ib.pk)
                    fa.import_batch = ib
                fa.save()
                fi.attempt = fa
            fi.save()
            previous_id_remap[(orig_fi_pk, current_month)] = fi.pk
            if delay_dup:
                delayed_duplicates[(orig_duplicate_of_id, current_month)] = fi.pk
    # let's deal with delayed stuff
    for dup_key, fi_pk in delayed_duplicates.items():
        dup_id = previous_id_remap[dup_key]  # must succeed now
        fetchintention_model.objects.filter(pk=fi_pk).update(duplicate_of_id=dup_id)
