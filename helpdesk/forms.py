from django import forms
from django.conf import settings


from .models import Ticket


class ReplyForm(forms.Form):
    message = forms.CharField(widget = forms.Textarea(attrs={"cols":90, "rows":10}))
    # message_markup_type


class AttachmentForm(forms.Form):

    def clean_file(self):
        if self.cleaned_data['file']:
            memfile = self.cleaned_data['file']
            if memfile.size > settings.ATTACHMENT_SIZE_LIMIT:
                raise forms.ValidationError(_('Attachment is too big'))
            return self.cleaned_data['attachment']


class TicketStatusForm(forms.Form):
    status = forms.ChoiceField(choices=Ticket.TICKET_STATUS_CHOICES, label=_(_('Ticket status'))


class TicketProblemCategoryForm(forms.Form):
    problem_category = forms.ModelChoiceField(query=TicketProblemCategory.objects.all(), label=_('Problem category'))
    
    
class AssigneeForm(forms.Form):
    assignee = forms.ModelChoiceField(query=User.objects.filter(is_staff=True), label=_('Assignee'))