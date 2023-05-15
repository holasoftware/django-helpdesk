from urllib.parse import urlencode
import datetime


from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.admin.filters import DateFieldListFilter
from django.utils.translation import gettext as _
from django.urls import reverse, path
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.shortcuts import get_object_or_404, render

# Register your models here.

from .models import User, CustomerSupportAgent, Customer, Ticket, TicketAttachment, TicketComment, TicketCommentAttachment, TicketInternalNote, TicketTag, TicketMeta, TicketProblemCategory


class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "displayed_name", "is_staff", "is_customer", "is_active")
    list_filter = ("is_staff", "is_customer", "is_superuser", "is_active", "groups")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("displayed_name","email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_customer",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    def has_module_permission(self, request):
        return True

    def has_view_permission(self, request, obj=None):
        return True
   

class AgentNameMixin:
    def agent_name(self, obj):
        return obj.customer_support_agent.username
    agent_name.short_description = _("Agent name")


class TicketLinkMixin:
    def ticket_link(self, obj):
        ticket_url = obj.ticket.get_url()
        return mark_safe('<a href="%s">%s</a>' % (ticket_url, obj.ticket.id))

    ticket_link.short_description = _("Ticket")


class TicketMetaAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket_link', 'name', 'value')
    def ticket_link(self, obj):
        ticket_url = obj.ticket.get_url()
        return '<a href="%s">%s</a>' % (ticket_url, obj.ticket.id)

    ticket_link.short_description = _("Ticket")

'''
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_superuser')
 ''' 
 
# TODO: Admin sortable for TicketProblemCategory
class TicketAttachmentInline(admin.TabularInline):
    model = TicketAttachment
    extra = 0
    
    def has_add_permission(self, request, obj):
        if obj is None or request.user.is_superuser:
            return True
            
        if obj.assigned_user == request.user:
            return True
        else:
            return False        

    def has_change_permission(self, request, obj=None):
        if obj is None or request.user.is_superuser:
            return True
            
        if obj.assigned_user == request.user:
            return True
        else:
            return False

    def has_delete_permission(self, request, obj=None):
        if obj is None or request.user.is_superuser:
            return True
            
        if obj.assigned_user == request.user:
            return True
        else:
            return False


class AgentFilter(admin.SimpleListFilter):
    title = _('Agent')
    parameter_name = 'assignee__username'
    
    def lookups(self, request, model_admin):
        return [(agent.username, agent.username) for agent in User.objects.filter(is_staff=True)]

    def queryset(self, request, queryset):
        return queryset


class CustomDateFieldListFilter(DateFieldListFilter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        now = timezone.now()
        # When time zone support is enabled, convert "now" to the user's time
        # zone so Django's definition of "Today" matches what the user expects.
        if timezone.is_aware(now):
            now = timezone.localtime(now)

        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        tomorrow = today + datetime.timedelta(days=1)
        
        self.links = list(self.links)
        self.links.insert(2, (
            _("Yesterday"),
            {
                self.lookup_kwarg_since: str(today - datetime.timedelta(days=1)),
                self.lookup_kwarg_until: str(tomorrow),
            },
        ))
        self.links.insert(3, (
            _("Past 2 days"),
            {
                self.lookup_kwarg_since: str(today - datetime.timedelta(days=2)),
                self.lookup_kwarg_until: str(tomorrow),
            },
        ))
        self.links.insert(4, (
            _("Past 3 days"),
            {
                self.lookup_kwarg_since: str(today - datetime.timedelta(days=3)),
                self.lookup_kwarg_until: str(tomorrow),
            },
        ))
        self.links.insert(5, (
            _("Past 4 days"),
            {
                self.lookup_kwarg_since: str(today - datetime.timedelta(days=4)),
                self.lookup_kwarg_until: str(tomorrow),
            },
        ))

        self.links.insert(6, (
            _("Past 5 days"),
            {
                self.lookup_kwarg_since: str(today - datetime.timedelta(days=5)),
                self.lookup_kwarg_until: str(tomorrow),
            },
        ))
        
        self.links.insert(7, (
            _("Past 6 days"),
            {
                self.lookup_kwarg_since: str(today - datetime.timedelta(days=6)),
                self.lookup_kwarg_until: str(tomorrow),
            },
        ))
        
        self.links.insert(9, (
            _("Past 14 days"),
            {
                self.lookup_kwarg_since: str(today - datetime.timedelta(days=3)),
                self.lookup_kwarg_until: str(tomorrow),
            },
        ))


class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'customer_name', 'customer_email', 'status', 'priority', 'assignee', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [TicketAttachmentInline]
    search_fields = ['subject', 'body', 'customer__name', 'customer__email']

    list_filter = ['priority', 'status', 'problem_category',  AgentFilter, ('date', CustomDateFieldListFilter)]
    
    #change_form_template = 'helpdesk/ticket_change_form.html'

    def get_list_display(self, request):
        list_display = ['id_link', 'subject_link', 'customer_name', 'customer_email', 'status', 'priority', 'assignee', 'created_at', 'updated_at']
        
        if request.user.is_superuser:
            list_display.append('edit_ticket_link')
        return list_display
        
    def edit_ticket_link(self, obj):
        url = reverse('admin:helpdesk_ticket_change', args=(obj.id,))

        return mark_safe('<a href="%s">Edit</a>' % url)
    edit_ticket_link.short_description = ''

    def id_link(self, obj):
        url = obj.get_helpdesk_comments_url()
        return mark_safe('<a href="%s">%s</a>' % (url, obj.id))
    id_link.short_description = _("Id")

    def subject_link(self, obj):
        url = obj.get_helpdesk_comments_url()
        return mark_safe('<a href="%s">%s</a>' % (url, obj.subject))
    subject_link.short_description = _("Subject")
    
    def customer_name(self, obj):
        return obj.customer.username
        
    def customer_email(self, obj):
        return obj.customer.email
        
    def get_urls(self):
        urls = super().get_urls()
        urls.insert(0, path('<int:ticket_id>/comments/', self.helpdesk_ticket_page_view, name='helpdesk_ticket_page'))
    
        return urls
    
    def helpdesk_ticket_page_view(self, request, ticket_id):
        ticket = get_object_or_404(Ticket, pk=ticket_id)
        comments_per_page = getattr(settings, 'TICKET_COMMENTS_PER_PAGE', None)
        if comments_per_page is None or comments_per_page is 0:
            is_paginated = False
            ticket_comments = Ticket.comments.all()
        else:
            is_paginated = True
            ticket_comments = Paginator(Ticket.comments.all(), comments_per_page)
            
        context= {
            **self.admin_site.each_context(request),
            'title': _('Ticket'),
            'ticket':ticket
        }
        
        return render(request, 'helpdesk/ticket_comments.html', context)
    
    def latest_activity(self, obj):
       latest = obj.get_latest_comment()
       return "%s %s - %s" % (date_template_filter(latest.date), time_template_filter(latest.date), latest.author)
    latest_activity.short_description = _("Latest activity")

    def has_module_permission(self, request):
        return True

    def has_view_permission(self, request, obj=None):
        return True
            
    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        if obj is None or request.user.is_superuser or obj.opened_by == request.user:
            return True
        else:
            return False

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:      
            obj.assignee = request.user
            
        return super().save_model(request, obj, form, change)
        
    def get_fields(self, request, obj=None):
        fields = ['problem_category','status', 'priority',  'customer', 'subject', 'body']
        if request.user.is_superuser:      
            fields.append('assignee')
            
        return fields


class TicketCommentAdmin(TicketLinkMixin, admin.ModelAdmin):
    list_display = ('id', 'ticket_link', 'date', 'agent_name')

    def agent_name(self, obj):
        if obj.customer_support_agent is not None:
            return obj.customer_support_agent.username
        else:
            return ''
    agent_name.short_description = _("Agent name")

    def has_module_permission(self, request):
        return True

    def has_view_permission(self, request, obj=None):
        return True

      
class TicketInternalNoteAdmin(AgentNameMixin, TicketLinkMixin, admin.ModelAdmin):
    list_display = ['id', 'ticket_link', 'agent_name', 'created_at', 'updated_at']

    def has_module_permission(self, request):
        return True

    def has_view_permission(self, request, obj=None):
        return True


class TicketTagAdmin(TicketLinkMixin, admin.ModelAdmin):
    list_display = ['id', 'ticket_link', 'tag_name', 'added_datetime']

    def has_module_permission(self, request):
        return True

    def has_view_permission(self, request, obj=None):
        return True


class TicketProblemCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'order')

    def has_module_permission(self, request):
        return True

    def has_view_permission(self, request, obj=None):
        return True


class TicketCommentAttachmentAdmin(TicketLinkMixin, admin.ModelAdmin):
    list_display = ('id', 'ticket_link', 'comment_link', 'mimetype', 'file_link')

    def comment_link(self):
        comment_url = reverse(
            "admin:helpdesk_comment_change",
            args=(str(obj.comment.id),),
            current_app=self.admin_site.name,
        )
        return '<a href="%s">%s</a>' % (comment_url, obj.comment.id)
    comment_link.short_description = _("Comment")
        
    def get_file_link_url(self, obj):
        pass
        
    def file_link(self, obj):
        return "<a href='%s'>%s</a>" % (self.get_file_link_url(obj), self.file_name)

    def has_module_permission(self, request):
        return True

    def has_view_permission(self, request, obj=None):
        return True


class TicketAttachmentAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return True

    def has_view_permission(self, request, obj=None):
        return True


class HelpdeskAdminSite(admin.AdminSite):
    site_header = _('Support ticket system')
    site_title = _('Helpdesk admin interface')
    index_title = _('Helpdesk index')
    
    enable_nav_sidebar = False

    logout_template = 'helpdesk/logout.html'
    # Text to put at the top of the admin index page.

    def logout(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        
        extra_context.update({
            'next': urlencode([
                (REDIRECT_FIELD_NAME,  reverse('admin:helpdesk_ticket_changelist', current_app=self.name))
            ])
        })
        return super().logout(request, extra_context)

            
admin_site = HelpdeskAdminSite('helpdesk_adminsite')

admin_site.register(User, UserAdmin)
admin_site.register(Ticket, TicketAdmin)
admin_site.register(TicketAttachment, TicketAttachmentAdmin)
admin_site.register(TicketMeta, TicketMetaAdmin)
admin_site.register(TicketComment, TicketCommentAdmin)
admin_site.register(TicketCommentAttachment, TicketCommentAttachmentAdmin)
admin_site.register(TicketInternalNote, TicketInternalNoteAdmin)
admin_site.register(TicketTag, TicketTagAdmin)
admin_site.register(TicketProblemCategory, TicketProblemCategoryAdmin)