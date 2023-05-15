# -*- encoding: utf-8 -*-
from django.dispatch import Signal

new_comment_from_client = Signal()

new_answer = Signal()

ticket_pre_created = Signal()

ticket_post_created = Signal()

ticket_updated = Signal()
