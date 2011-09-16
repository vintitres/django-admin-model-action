from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect


ACTION_DESCRIPTION_NAME = 'short_description'
ACTION_CAN_CALL_FUNC_NAME = 'can_add_action'
ACTION_DONE_REDIRECT_URL = 'redirect_url'

class ModelAction(AdminAction):
    form_prefix = "__model_action-"

    @property
    def name(self):
        if hasattr(self, 'action_name'):
            return self.action_name
        raise NotImplementedError

    @property
    def form_name(self):
        return u"%s%s" % (self.form_prefix, self.name.lower().replace(" ", "-"))

    def can_act_for(self, request, obj):
        return True

    def do_action(self, request, obj):
        raise NotImplementedError

    def get_redirect_url(self, request, obj):
        return None

    def __unicode__(self):
        return u"ModelAction %s" % self.action_name.__name__

class ProxyModelAction(ModelAction):

    def __init__(self, action_method, model):
        if not callable(action_method):
            action_method = getattr(model, action_method)
        self.action_method = action_method
        self.action_name = getattr(self.action_method, ACTION_DESCRIPTION_NAME,  u"Model Action (please set a 'short_description' attribute on your method '%s')" % (self.action_method.__name__))
        self.can_add_action = getattr(self.action_method, ACTION_CAN_CALL_FUNC_NAME, None)
        self.redirect_url = getattr(self.action_method, ACTION_DONE_REDIRECT_URL, None)

    def can_act_for(self, request, obj):
        if self.can_add_action:
            return self.can_add_action( request, obj)
        return True

    def do_action(self, request, obj):
        msg =  self.action_method(request, obj)
        if msg is None:
            msg = "%s is done." % self.action_name
        messages.success(request, msg)

    def get_redirect_url(self, request, obj):
        if self.redirect_url:
            return self.redirect_url(request, obj)
        return None
            
class ActionAdmin(admin.ModelAdmin):
    model_actions = []

    change_form_template = "adminmodelaction/model-action-change-form.html"
    
    def __init__(self, model, admin_site):
        super(ActionAdmin, self).__init__(model, admin_site)
        model_actions = [] 
        for action_option in self.model_actions:
            if issubclass(action_option, ModelAction):
                model_actions.append(action_option())
            else:
                model_actions.append(ProxyModelAction(action_options, model))
        self.model_actions = model_actions

    def get_model_actions_for(self, request, obj):
        return [action for action in self.model_actions if action.can_act_for ( request, obj)]

    def change_view(self, request, object_id, extra_context=None):
        if extra_context is None:
            extra_context = {}
        obj = self.get_object(request, admin.util.unquote(object_id))    
        extra_context['model_actions'] = self.get_model_actions_for(request, obj)
        if request.POST.has_key('is_model_action'):
            for action in self.model_actions:
                form_name = action.form_name
                if request.POST.has_key(form_name):
                    action.do_action(request, obj)
            redirect_url = action.get_redirect_url(request, obj) or request.path
            response = HttpResponseRedirect(redirect_url)
        else:
            response =  super(ActionAdmin, self).change_view(request, object_id, extra_context)
        return response
