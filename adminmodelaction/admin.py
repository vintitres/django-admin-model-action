from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect


ACTION_DESCRIPTION_NAME = 'short_description'
ACTION_CAN_CALL_FUNC_NAME = 'can_add_action'
ACTION_DONE_REDIRECT_URL = 'redirect_url'


class ModelAction(object):
    form_prefix = "__model_action-"

    @property
    def name(self):
        if hasattr(self, 'action_name'):
            return self.action_name
        raise NotImplementedError

    @property
    def form_name(self):
        return u"%s%s" % (self.form_prefix,
                self.name.lower().replace(" ", "-"))

    def can_act_for(self, request, obj):
        return True

    def do_action(self, request, obj):
        raise NotImplementedError

    def get_redirect_url(self, request, obj):
        return None

    def __unicode__(self):
        return u"ModelAction %s" % self.action_name


class ProxyModelAction(ModelAction):

    def __init__(self, action_method, model):
        if not callable(action_method):
            action_method = getattr(model, action_method)
        self.action_method = action_method
        self.action_name = getattr(self.action_method, ACTION_DESCRIPTION_NAME,
                u"Model Action (please set a 'short_description' attribute on "
                "your method '%s')" % (self.action_method.__name__))
        self.can_add_action = getattr(self.action_method,
                ACTION_CAN_CALL_FUNC_NAME, None)
        self.redirect_url = getattr(self.action_method,
                ACTION_DONE_REDIRECT_URL, None)

    def can_act_for(self, request, obj):
        if self.can_add_action:
            return self.can_add_action(obj, request)
        return True

    def do_action(self, request, obj):
        msg = self.action_method(obj, request)
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
        import inspect
        super(ActionAdmin, self).__init__(model, admin_site)
        model_actions = []
        for action_option in self.model_actions:
            if inspect.isclass(action_option) and issubclass(action_option,
                    ModelAction):
                model_actions.append(action_option())
            else:
                model_actions.append(ProxyModelAction(action_option, model))
        self.model_actions = model_actions

    def get_model_actions_for(self, request, obj):
        return [action for action in self.model_actions
                if action.can_act_for(request, obj)]

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if extra_context is None:
            extra_context = {}
        obj = self.get_object(request, admin.util.unquote(object_id))
        if obj is not None:
            extra_context['model_actions'] = \
                    self.get_model_actions_for(request, obj)
            if 'is_model_action' in request.POST:
                redirect_url = request.path
                for action in self.model_actions:
                    form_name = action.form_name
                    if form_name in request.POST:
                        action.do_action(request, obj)
                        redirect_url = action.get_redirect_url(request, obj) \
                                or redirect_url
                response = HttpResponseRedirect(redirect_url)
            else:
                response = super(ActionAdmin, self).change_view(request,
                        object_id, form_url, extra_context)
        else:
            response = super(ActionAdmin, self).change_view(request, object_id,
                    form_url, extra_context)
        return response
