class UserTrackMixin:
    def form_valid(self, form):
        if not form.instance.pk:  # رکورد جدید
            form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)