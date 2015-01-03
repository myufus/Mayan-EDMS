import logging

from mayan.celery import app
from documents.models import Document
from lock_manager import Lock, LockError

from .api import update_indexes, delete_indexes
from .tools import do_rebuild_all_indexes

logger = logging.getLogger(__name__)
RETRY_DELAY = 20  # TODO: convert this into a config option


@app.task(ignore_result=True)
def task_delete_indexes(document_id):
    document = Document.objects.get(pk=document_id)
    delete_indexes(document)


@app.task(bind=True, ignore_result=True)
def task_update_indexes(self, document_id):
    try:
        lock = Lock.acquire_lock('document_indexing_task_update_index_document_%d' % document_id)
    except LockError as exception:
        # This document is being reindexed by another task, retry later
        raise self.retry(exc=exception, countdown=RETRY_DELAY)
    else:
        try:
            document = Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            # Document was deleted before we could execute, abort about updating
            pass
        else:
            update_indexes(document)


@app.task(ignore_result=True)
def task_do_rebuild_all_indexes():
    # TODO: Find a way to rebuild after all pending updates are finished
    do_rebuild_all_indexes()
