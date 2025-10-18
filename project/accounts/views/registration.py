from django.contrib.auth.views import LoginView as BaseLoginView


class CustomLoginView(BaseLoginView):
    def form_valid(self, form):
        response = super().form_valid(form)
        if hasattr(self.request, "set_lang_cookie"):
            response = self.request.set_lang_cookie(response)
        return response
