import base64
import os
import uuid
import mimetypes


from django.conf import settings
from django.contrib.auth.models import PermissionsMixin, UserManager as DjangoUserManager
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.urls import reverse
from django.db import models
from django.db.models.signals import post_save
from django.db.models.signals import post_save as signal_post_save, post_delete as signal_post_delete
from django.dispatch import receiver
from django.dispatch import receiver as signal_receiver
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.utils.timezone import now as local_date_time_now

from helpdesk.signals import new_comment_from_client, ticket_updated, new_answer, ticket_pre_created, ticket_post_created

"""
class WordpressInstallation(models.Model):
    customer = models.ForeignKey(User)
    url = models.CharField(max_length=64, primary_key=True)
    database_username = models.CharField(max_length=100)
    database_password = models.CharField(max_length=100)
    key = models.CharField(max_length=255, blank=True, null=True, unique=True)
    
    default_assignee = models.ForeignKey(User, blank=True, null=True)

    def __str__(self):
        return self.url"""


# SupportTeamMemberModel, TicketSupportUserModel, TicketingSupportUserModel
# member_support_team, customer_support_agent, support_team_user
# CustomerSupportUserModel, User

# Si solamente existe una categoria, esta entonces no se muestra.
# TicketProblemCategoryModel


# TicketNotificationEmailTemplateModel
class UserManager(DjangoUserManager):
    def create_customer_support_agent(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Customer support agent must have is_staff=True.")

        return self._create_user(username, email, password, **extra_fields)

    def create_customer(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_customer", True)

        if extra_fields.get("is_customer") is not True:
            raise ValueError("Customer must have is_customer=True.")

        return self._create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    An abstract base class implementing a fully featured User model with
    admin-compliant permissions.

    Username and password are required. Other fields are optional.
    """

    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_(
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        ),
        validators=[username_validator],
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )
 
    displayed_name = models.CharField(_("displayed name"), max_length=150, blank=True)

    email = models.EmailField(_("email address"), blank=True)
    
    is_customer = models.BooleanField(default=False)

    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    date_joined = models.DateTimeField(_("date joined"), default=local_date_time_now)

    objects = UserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def set_random_password(self):
        random_password = self.__class__.make_random_password()
        self.set_password(random_password)
        return random_password
 
    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)


class CustomerSupportAgent(User):
    class Meta:
        proxy = True
        verbose_name = _("Customer Support Agent")
        verbose_name_plural = _("Customer Support Agents")

    def get_comments(self):
        return self.comments_as_agent.all()
    
    def get_num_comments(self):
        return self.get_comments().count()
              
    def get_num_tickets(self):
        return self.opened_tickets_as_agent.all().count()


class CustomerManager(UserManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_customer=True)

class Customer(User):
    class Meta:
        proxy = True
        verbose_name = _("customer")
        verbose_name_plural = _("customers")

    def get_comments(self):
        return TicketComment.objects.filter(ticket__customer=self, customer_support_agent=None)
    
    def get_num_comments(self):
        return self.get_comments().count()
              
    def get_num_tickets(self):
        return self.tickets.all().count()
        

# TicketCustomerUnreadCommentsModel.objects.num_unread_comments_from(customer)
# TicketTrackersModel
# TicketReadTrackerModel



def ticket_attachment_path(instance, filename):
    path = os.path.join(settings.FILE_ROOT, 'file_attachments', uuid.uuid4().hex)
    return path


#class TicketProblemCategoryModel(MPTTModel):
class TicketProblemCategory(models.Model):
    # title
    name = models.CharField(max_length=100, blank=False, null=False, unique=True)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=100, verbose_name=_("order"))
    # parent = models.ForeignKey('self', blank=True, null=True)
#    parent = TreeForeignKey(
#        'self',
#        related_name='children',
#        null=True, blank=True,
#        on_delete=models.SET_NULL,
#        verbose_name='parent category')


    # objects = TreeManager()

    def __str__(self):
        return self.name

    @classmethod
    def total_categories(cls):
        return cls.objects.all().count()

    @property
    def num_tickets(self):
        return self.tickets.count()
        
    def last_ticket(self):
        if self.tickets.count() == 0:
            return None

        ticket = self.tickets.order_by('-date')[0]
        return ticket
    
    def get_tickets(self):
        return Tickets.objects.filter(problem_category=self)

    class Meta:
        verbose_name = _("Ticket Problem Category")
        verbose_name_plural = _("Ticket Problem Categories")
        #ordering = ('position', 'title')
        ordering = ('order', 'name')

    # get_new_reference


class TicketManager(models.Manager):
    def get_closed_tickets(self):
        return self.filter(status__in = [self.model.TICKET_CLOSED_STATUSES])

    def get_opened_tickets(self):
        return self.filter(status__in = [self.model.TICKET_OPEN_STATUSES])

# La idea es que sea el equipo de soporte el que asocie metadatos al ticket. El cliente es orientado y guiado. No se espera que haga cosas que no sabe hacer.
# Cualquier edición en los tags o cambio de categoria se registra en el modelo de eventos
# - ModifiedTag
# - ModifiedCategory

# customer_support_agent
class Ticket(models.Model):
    # List of available status options
    # When status is resolved or closed is not possible to add more comments
    
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    # Very High
    CRITICAL = 3


    PRIORITY_CHOICES = (
        (CRITICAL, _('Critical')),
        (HIGH, _('High')),
        (MEDIUM, _('Medium')),
        (LOW, _('Low')),
    )

    #NEW_STATUS = 0
    #ANSWERING_STATUS = 1
    OPEN_STATUS = 0
    IN_PROGRESS_STATUS = 1
    PAUSED_STATUS = 2

    # ISSUE_SOLVED_STATUS
    # CANCELLED_BY_CUSTOMER_STATUS = 2
    RESOLVED_STATUS = 3
    CLOSED_BY_CUSTOMER_STATUS = 4
    CLOSED_BY_SUPPORT_AGENT_STATUS = 5
    CLOSED_FOR_INACTIVITY_STATUS = 6
    INVALID_STATUS = 7
    DUPLICATE_STATUS = 8

    TICKET_OPEN_STATUSES = [OPEN_STATUS, IN_PROGRESS_STATUS]

    # List of statuses that define a ticket as finally closed
    TICKET_CLOSED_STATUSES = [RESOLVED_STATUS, CLOSED_BY_CUSTOMER_STATUS, CLOSED_BY_SUPPORT_AGENT_STATUS, CLOSED_FOR_INACTIVITY_STATUS, INVALID_STATUS, DUPLICATE_STATUS]

    TICKET_STATUSES = TICKET_OPEN_STATUSES + TICKET_CLOSED_STATUSES


    TICKET_STATUS_CHOICES = (
        (OPEN_STATUS, _("Open")),
        (IN_PROGRESS_STATUS, _('In progress')),
        (PAUSED_STATUS, _('Paused')),
        (RESOLVED_STATUS, _("Resolved")),
        (CLOSED_BY_CUSTOMER_STATUS, _("Closed by customer")),
        (CLOSED_BY_SUPPORT_AGENT_STATUS, _("Closed by support agent")),
        (CLOSED_FOR_INACTIVITY_STATUS, _("Closed for inactivity")),
        (INVALID_STATUS, _("Invalid")),
        (DUPLICATE_STATUS, _("Duplicate"))
    )

    RATE_CHOICES = (
        (1, _("Unsatisfied")),
        (2, _("Regular")),
        # (2, "It could be better"),
        (3, _("Ok")),
        (4, _("Good")),
        (5, _("Excellent"))
    )

    # customer and reference should be unique together
    # reference = models.PositiveIntegerField(_('Reference'), unique=True, db_column='reference')
    uuid = models.UUIDField(_('UUID'), unique=True, default=uuid.uuid4, editable=False)
        # category

    problem_category = models.ForeignKey(TicketProblemCategory, blank=True, null=True, on_delete=models.CASCADE, related_name="tickets", db_column="problem_category")

    status = models.SmallIntegerField(_("Status"), choices=TICKET_STATUS_CHOICES, default=OPEN_STATUS, db_column='status')
    priority = models.SmallIntegerField(_("Priority"), choices=PRIORITY_CHOICES, db_index=True, default=MEDIUM)   
    customer = models.ForeignKey(Customer, verbose_name=_("Customer"), related_name='customer_tickets', on_delete=models.CASCADE)
     

    date = models.DateTimeField(_("Date"), auto_now_add=True)
    opened_by = models.ForeignKey(CustomerSupportAgent, verbose_name=_("Opened by"), null=True, blank=True, help_text=_("Support team member opening the ticket. Null if it was the customer the one opening the ticket"), related_name='opened_tickets_as_agent', on_delete=models.CASCADE)


    closed_by = models.ForeignKey(CustomerSupportAgent, verbose_name=_("Closed by"), null=True, blank=True, on_delete=models.CASCADE)
    date_closed = models.DateTimeField(_("Date closed"), null=True, blank=True)    
    reason_closed = models.TextField(_("Reason closed"), null=True, blank=True)
        
    #assigned_user
    assignee = models.ForeignKey(
        CustomerSupportAgent,
        blank=True,
        null=True,
        db_index=True,
        on_delete=models.CASCADE,
        related_name="assigned_tickets",
        #limit_choices_to={'groups__name': 'Helpdesk support'}
    )

    subject = models.CharField(_("Subject"), max_length=255)

    body = models.TextField(
        null=True,
        blank=True
    )
    
    # closed_by
    # reason_closed
    # is_resolved
    # is_closed


    #description = models.TextField(_("Description"), help_text=_("A detailed description of your problem."), db_column='description')

    # After closing a ticket the customer is asked for an evaluation. The customer shouldnt be forced to rate (?)
    rate = models.SmallIntegerField(_('Rate'), choices=RATE_CHOICES, blank=True, null=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = TicketManager()
    

    class Meta:
        verbose_name = _("Ticket")
        verbose_name_plural = _("Tickets")
        ordering = ('priority', 'date')

        permissions = (
            ("view_customer", "Can view ticket customer"),
            ("view_tickets", "Can view tickets"),
            ("view_all_tickets", "Can view tickets assigned to other users"),
        )
        #ordering = ['-created_at', 'title']

    # get_new_reference

    def get_helpdesk_comments_url(self):
        return reverse('admin:helpdesk_ticket_page', kwargs={'ticket_id':self.id})

    def get_admin_url(self):
        ticket_url = reverse(
            "admin:helpdesk_ticket_change",
            args=(str(self.id),)
        )
        return ticket_url
        
    # get_participants
    def get_support_team_members_commenting(self):
        return CustomerSupportAgent.objects.filter(comments__ticket=self).distinct()

    @property
    def author(self):
        if self.opened_by is None:
            return self.customer
        else:
            return self.opened_by

    @property
    def is_opened_by_customer(self):
        return self.opened_by is None

    @property
    def is_opened_by_customer_support_agent(self):
        return self.opened_by is not None

    def get_latest_comment(self, is_customer=None):
        if is_customer is not None:
            if is_customer:
                filter_kwargs = {
                    "customer_support_agent__isnull": True
                }
            else:
                filter_kwargs = {
                    "customer_support_agent__isnull": False
                }
        else:
            filter_kwargs = None

        try:
            if filter_kwargs is None:
                latest_comment = self.comments.latest('date')            
            else:
                latest_comment = self.comments.filter(**filter_kwargs).latest()
        except TicketComment.DoesNotExist:
            return None

        return latest_comment

    @property
    def is_last_reply_from_customer(self):
        comment = self.get_latest_comment()

        if comment is None:
            return None
        else:
            return comment.is_from_customer


    def get_comments_count(self):
        return self.comments.count()

    def get_customer_comments(self):
        return self.comments.filter(customer_support_agent__isnull=True)

    def get_customer_comments_count(self):
        return self.get_customer_comments().count()

    def get_customer_support_agent_comments(self):
        return self.comments.filter(customer_support_agent__isnull=False)

    def get_customer_support_agent_comments_count(self):
        return self.get_customer_support_agent_comments().count()

    def get_support_team_comments(self):
        return self.comments.filter(customer_support_agent__isnull=False)

    # get_support_team_members_commenting, get_active_customer_support_agents, get_active_support_team_members

#    def num_new_comments_for_customer(self):
#        pass


    @property
    def closed(self):
        return self.status in CLOSED_STATUSES

    def is_answered(self):
        try:
            latest = self.get_latest_comment()
        except TicketComment.DoesNotExist:
            return False
        return latest.author != self.creator
    is_answered.boolean = True
    is_answered.short_description = _("Is answered")


    def is_closed(self):
        return self.status in self.TICKET_CLOSED_STATUSES

    def closed_by_the_customer(self):
        self.date_closed = local_date_time_now()
        self.status = self.CLOSED_BY_CUSTOMER_STATUS
        self.save(update_fields=('status', 'date_closed'))

    def closed_by(self, user):
        self.date_closed = local_date_time_now()
        self.closed_by = user
        self.status = self.CLOSED_BY_THE_ADMIN_STAFF_STATUS
        self.save(update_fields=('status', 'date_closed'))

    def resolved(self):
        self.date_closed = local_date_time_now()
        self.status = self.RESOLVED_STATUS
        self.save(update_fields=('status', 'date_closed'))

    def close_for_inactivity(self):
        # after closing a ticket is not possible to do any change
        self.date_closed = local_date_time_now()
        self.status = self.CLOSED_FOR_INACTIVITY_STATUS
        self.save(update_fields=('status', 'date_closed'))

    def is_answered(self):
        if self.is_closed:
             return True

        latest_comment = self.latest_comment
        if latest_comment is None:
            return False

        return latest_comment.customer_support_agent != None

    is_answered.boolean = True
    is_answered.short_description = _("Is answered")

    def reply(self, text, agent=None, state='resolved'):
        answer = Comment.objects.create(
            ticket=self,
            body=text,
            author=author
        )
        self.save()
        new_answer.send(sender=self.__class__, ticket=self, answer=answer)
        
        return answer

    def rate(self, rate):
        if self.is_closed():
            if self.rate is None:
                self.rate = rate
                super().save()
            else:
                raise StandardError('Ticket was already rated.')


    def notify(self, message=None, content=None):
        """ Send an email to ticket stakeholders notifying an state update """
        emails = self.get_notification_emails()
        template = 'issues/ticket_notification.mail'
        html_template = 'issues/ticket_notification_html.mail'
        context = {
            'ticket': self,
            'ticket_message': message
        }
        send_email_template(template, context, emails, html=html_template)

    def is_involved_by(self, agent):
        return self.comments.filter(customer_support_agent=agent).exists()
    
#    def get_cc_emails(self):
#        return self.cc.split(',') if self.cc else []
    # TODO: A revisar

      
    @property
    def priority_label(self):
        return self.PRIORITY_CHOICES[self.priority][1]

    @property
    def status_verbose(self):
        return self.TICKET_STATUS_CHOICES[self.status][1]

    @property
    def status_label(self):
        return self.STATUS_CHOICES[self.status][1]
        
    def filter_by_tag(self, tag_name):
        return self.objects.filter(tag__tag_name=tag_name).all()

    # Crear automaticamente subscripcion en el trackers: TicketCommentsReadTrackerModel
    def save(self, *args, **kwargs):
        if self.is_closed():
            raise StandardError("Not possible to modify ticket because its closed.")
        else:
            # if self.rate is not None:
            if isinstance(self.rate, int):
                raise StandardError("Not possible to rate ticket because ticket it's still in progress.")

        super().save(*args, **kwargs)

    def __str__(self):
        return "#%s %s" % (self.id, self.subject)

    def __repr__(self):
        return "<Ticket '{}'>".format(self.id)
  

class TicketMetaManager(models.Manager):
    def get_value(self, ticket, name):
        try:
            return super().get(ticket=ticket, name=name).value
        except self.model.DoesNotExists:
            pass


class TicketMeta(models.Model):
    ticket = models.ForeignKey(Ticket, verbose_name=_("Ticket"), related_name="metadata", on_delete=models.CASCADE)    
    name = models.CharField(max_length=100)
    value = models.JSONField()

    objects = TicketMetaManager()

    class Meta:
        unique_together = ('ticket', 'name')
        verbose_name = _('Ticket Metadata')
        verbose_name_plural = _('Ticket Metadata')

        indexes = [
            models.Index(fields=['ticket', 'name']),
        ]
        
    def __str__(self):
        return '#%d %s' % (self.ticket.id, self.name)

  



attachment_fs = FileSystemStorage(location=settings.BASE_DIR / 'attachments',
                                  base_url='/helpdesk/attachments/')

class TicketAttachment(models.Model):
    """
    Represents a file attached to a follow-up. This could come from an e-mail
    attachment, or it could be uploaded via the web interface.
    """

    ticket = models.ForeignKey(Ticket, verbose_name=_("Ticket"), related_name='attachments', on_delete=models.CASCADE, db_index=True)

    # file = models.FileField(upload_to='tickets', storage=attachment_fs)

    file = models.FileField(
        _('File'),
        upload_to=ticket_attachment_path,
        max_length=1000
    )

    mime_type = models.CharField(
        _('MIME Type'),
        blank=True,
        max_length=255
    )


    class Meta:
        verbose_name = _('Ticket Attachment')
        verbose_name_plural = _('Ticket Attachments')


    def __str__(self):
        return str(self.file)

    @property
    def filename(self):
        return os.path.basename(self.attachment.name)

    @property
    def signed_url(self):
        signer = Signer()
        return reverse('helpdesk_attachment', args=[signer.sign(self.pk)])

    def save(self, *args, **kwargs):
        filename = str(self.file)

        if not self.mime_type:
            self.mime_type = \
                mimetypes.guess_type(filename, strict=False)[0] or \
                'application/octet-stream'

        return super().save(*args, **kwargs)


class TicketTag(models.Model):
    ticket = models.ForeignKey(Ticket, verbose_name=_("Ticket"), related_name='tags',  on_delete=models.CASCADE)
    tag_name = models.CharField(max_length=50)
    added_datetime = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('ticket Tag')
        verbose_name_plural = _('Ticket Tags')
        unique_together = ('ticket', 'tag_name')
        ordering = ['added_datetime']

    def __str__(self):
        return self.tag_name

    def __repr__(self):
        return '<Tag \'{}\' for {}'.format(self.tag_name, self.ticket)

def tags_by_occurence_count(n=10):
    o = TicketTag.objects.values('tag_name') \
            .annotate(count=models.Count('tag_name')) \
            .order_by('-count')
    return [v['tag_name'] for v in list(o)[:n+1]]


class TicketInternalNote(models.Model):
    ticket = models.ForeignKey(Ticket, verbose_name=_("Ticket"), related_name='notes',  on_delete=models.CASCADE, db_index=True)

    customer_support_agent = models.ForeignKey(CustomerSupportAgent, verbose_name=_("Customer support agent"), null=True, blank=True, on_delete=models.SET_NULL, related_name='ticket_notes', limit_choices_to={'is_staff': True}, db_index=True)

    text = models.TextField(_("Text"), help_text=_("Text of the note."))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Ticket Internal Note")
        verbose_name_plural = _("Ticket Internal Notes")
        ordering = ['ticket', '-created_at']

'''
class FollowUp(models.Model):
    ticket= models.ForeignKey(Ticket, on_delete=models.CASCADE, db_index=True)
    followup_date = models.DateTimeField(auto_now_add=True)
    followup_user= models.ForeignKey(User, related_name='followup_user')

    class Meta:
        verbose_name = _('Follow Up')
        verbose_name_plural = _('Follow Ups')
'''

# The customer associated with the ticket is automatically subscribed when creating the ticket. The user staff is automatically subscribed when answering a ticket
class TicketCustomerSupportAgentReadTracker(models.Model):
    """Tracking the unread comments for the support team"""
    customer_support_agent = models.ForeignKey(CustomerSupportAgent, verbose_name=_("Customer support user"),  on_delete=models.CASCADE, related_name='read_comments_tracker', limit_choices_to={'is_staff': True}, db_index=True)

    ticket = models.ForeignKey(Ticket, verbose_name=_("Ticket"), on_delete=models.CASCADE, db_index=True)

    subscription_date = models.DateTimeField(auto_now_add=True, verbose_name=_("Subscription Date"))
    last_read_on = models.DateTimeField(auto_now=True)
    last_comment_id_read = models.BigIntegerField(editable=False)

    #last_comment_read = models.ForeignKey(TicketCommentModel, verbose_name=_("Last comment read"), on_delete=models.SET_NULL, db_column='last_comment_read')

    class Meta:
        verbose_name = _('Ticket Support Team Read Tracker')
        verbose_name_plural = _('Ticket Support Team Read Tracker')
        unique_together = ('customer_support_agent', 'ticket')

    def __str__(self):
        return 'User #%s following ticket #%d' % (self.ticket.id, self.followup_user.id)


#class TicketCustomerUnreadCommentsModel(models.Model):
#    comment = models.OneToOneField(TicketCommentModel, verbose_name=_("Comment"), on_delete=models.CASCADE, related_name='unread_tracking', db_column='comment')

    # is it new ticket for the user?
    # is_new = models.BooleanField(default=True, db_column='is_new')

    # customer_support_agent = models.ForeignKey(User, verbose_name=_("Support team"), null=True, blank=True, on_delete=models.CASCADE, db_column='customer_support_agent')

#    def add_unread_comments(self, new_comments=1):
#        self.new_comments += new_comments
#        self.save()

#    class Meta:
#        verbose_name = _('Ticket Customer Unread Comments')
#        verbose_name_plural = _('Ticket Customer Unread Comments')

#        db_table = "wp_hosting_admin__ticketcustomerunreadcomments"
   

class Notification(models.Model):
    ticket= models.ForeignKey(Ticket, on_delete=models.CASCADE, db_index=True)
    date = models.DateTimeField(auto_now_add=True)
    user= models.ForeignKey(CustomerSupportAgent, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False, editable=False)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')


# TicketPrivateMessageModel
# TicketSupportTeamDiscussionModel
# TicketSupportTeamNoteModel


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, verbose_name=_("Ticket"), related_name='comments', on_delete=models.CASCADE, db_index=True)
    date = models.DateTimeField(auto_now_add=True, verbose_name=_("Date"))

    customer_support_agent = models.ForeignKey(CustomerSupportAgent, verbose_name=_("Customer support user"), limit_choices_to={'is_staff': True}, null=True, blank=True, on_delete=models.CASCADE, related_name='comments_as_agent')

    text = models.TextField(_("Text"))
    #body = models.TextField()
    #raw_text = models.TextField()

    read = models.BooleanField(_("Did the customer read this comment?"), null=True, blank=True)
    notified = models.BooleanField(default=True, editable=False)

    class Meta:
        verbose_name = _("Ticket Comment")
        verbose_name_plural = _("Ticket Comments")
        ordering = ['date']

        get_latest_by = 'date'
    '''
    @property
    def text(self):
        """Pass the raw_text field through a Markdown parser and return its result."""
        return markdown(self.raw_text)'''


    def has_attachments(self):
        return self.attachments.count() > 0

    def get_position(self):
        return self.__class__.objects.filter(pk__lt=self.id).count() + 1


    @property
    def is_from_support_team(self):
        return self.customer_support_agent is not None

    @property
    def is_from_customer(self):
        return self.customer_support_agent is None

    def get_author_name(self):
        if self.customer_support_agent is None:
            return self.ticket.customer.displayed_name
        else:
            return self.customer_support_agent.username

    def __repr__(self):
        return '<Comment #{}>'.format(self.id)

    def __str__(self):
        return "Comment #%s on ticket #%s"%(self.id, self.ticket.id)

    def save(self, *args, **kwargs):
        if self.ticket.is_closed():
            raise StandardError('Not possible to add comments to a closed ticket.')
        super().save(*args, **kwargs)


class TicketCommentAttachment(models.Model):
    comment = models.ForeignKey(TicketComment, verbose_name=_("Ticket comment"), related_name='attachments',  on_delete=models.CASCADE, db_index=True)
    
    file = models.FileField(
        _('File'),
        upload_to=ticket_attachment_path,
        max_length=1000
    )

    file_name = models.TextField()

    mimetype = models.CharField(
        _('MIME Type'),
        blank=True,
        max_length=255,
    )


    class Meta:
        verbose_name = _('Ticket Comment Attachment')
        verbose_name_plural = _('Ticket Comment Attachments')


    def __str__(self):
        return str(self.file)

    def save(self, *args, **kwargs):
        if not isinstance(self.mimetype, str):
            self.mimetype = \
                mimetypes.guess_type(self.file_name, strict=False)[0] or \
                'application/octet-stream'

        super().save(*args, **kwargs)



@receiver(post_save, sender=TicketComment, dispatch_uid='on_comment_inserted')
def on_comment_inserted(sender, **kwargs):
    return
    if not kwargs['created']:
        return
    comment = kwargs['instance']
    if comment.is_from_customer:
        comment.ticket.status = Ticket.OPEN_STATUS
        comment.ticket.save(update_fields=('status',))
        new_comment_from_client.send(sender=sender, comment=comment, ticket=comment.ticket)


@receiver(ticket_post_created, sender=Ticket, dispatch_uid='on_ticket_save')
def on_ticket_save(sender, **kwargs):
    return

    ticket = kwargs['instance']
    if kwargs.get('author', None) != ticket.assignee:
        ticket.notify_assignee('Ticket created', 'helpdesk/ticket_created.html')


@receiver(ticket_updated, dispatch_uid='on_ticket_update')
def on_ticket_update(sender, **kwargs):
    return
    if kwargs['updater'] != kwargs['ticket'].assignee:
        kwargs['ticket'].notify_assignee('Ticket updated', 'helpdesk/ticket_updated.html',
                                         changes=kwargs['changes'], updater=kwargs['updater'])


@receiver(new_comment_from_client, dispatch_uid='on_new_client_comment')
def on_new_client_comment(sender, comment, ticket, **kwargs):
    return
    ticket.notify_assignee('Comment added', 'helpdesk/comment_added.html')


@receiver(new_answer, dispatch_uid='on_new_answer')
def on_new_answer(sender, ticket, answer, **kwargs):
    return
    if answer.author != ticket.assignee:
        ticket.notify_assignee('Answer added', 'helpdesk/answer_added.html', answer=answer)

    if not answer.internal:
        subject = 'Re: [HD-%d] %s' % (ticket.pk, ticket.title)
        try:
            ticket.notify_customer(subject, 'helpdesk/customer_answer.html',
                                   answer=answer, attachments=answer.attachments.all())
        except Exception as e:
            print('Error sending email:', e)
            import traceback
            traceback.print_exc()
            answer.notified = False
            ticket.state = State.objects.get(machine_name='open')

            answer.save()


class TicketChangeLog(models.Model):
    """
    Ticket change log model for record the changes of tickets objects.
    """
    ticket = models.ForeignKey(Ticket, verbose_name=_("Ticket"), related_name='status_changelogs', on_delete=models.CASCADE, db_index=True)

    date = models.DateTimeField(auto_now_add=True, verbose_name=_("Date"))

    # Es nulo si es el ciente el que cambio el valor del atributo
    customer_support_agent = models.ForeignKey(
        CustomerSupportAgent,
        on_delete=models.CASCADE,
        verbose_name=_('User'),
        limit_choices_to={'is_staff': True},
        db_index=True
    )

    field = models.CharField(
        _('Field'),
        max_length=100,
        choices = (
            ('status', _('Status')),
            ('priority', _('Priority')),
            ('problem_category', _('Problem category'))
        ),
        db_index=True
    )

    old_value = models.TextField(
        _('Old Value'),
        blank=True,
        null=True
    )

    new_value = models.TextField(
        _('New Value'),
        blank=True,
        null=True
    )

    class Meta:
        get_latest_by = 'date'
        ordering = ('ticket', 'date')

        verbose_name = _('Ticket change')
        verbose_name_plural = _('Ticket changes')

    def __str__(self):
        out = 'Ticket {ticket_id} at {date}: %s ' % (self.ticket.id, self.date.strftime('%Y-%m-%d %H:%M:%S'), self.field)
        if not self.new_value:
            out += _('removed')
        elif not self.old_value:
            out += _('set to %s') % self.new_value
        else:
            out += _('changed from "%(old_value)s" to "%(new_value)s"') % {
                'old_value': self.old_value,
                'new_value': self.new_value
            }
        return out
#    def __str__(self):
#        return ('{self.ticket_id} {date}: {self.before} ==> '
#                '{self.after}'.format(self=self,
#                                      date=self.date.strftime(
#                                          '%Y-%m-%d %H:%M:%S')))

class HistoryAction(models.Model):
    CHANGE_TYPES = (
        ('change status', 'Change status'),
        ('change priority', 'Change priority'),
        ('change assignee', 'Change assignee'),
        ('created comment', 'Created comment'),
        ('edited comment', 'Edited comment'),
        ('deleted comment', 'Deleted comment'),
        ('created internal note', 'Created internal note'),
        ('edited internal note', 'Edited internal note'),
        ('deleted internal note', 'Deleted internal note')
    )
    
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    customer_support_agent = models.ForeignKey(CustomerSupportAgent, limit_choices_to={'is_staff': True}, on_delete=models.CASCADE)
    change_type = models.CharField(choices=CHANGE_TYPES, max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
'''
class ChangeStatusAction(models.Model):
    history_action = models.ForeignKey(Ticket)
    '''
