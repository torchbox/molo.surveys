from wagtail.wagtailadmin.edit_handlers import BaseFieldPanel, FieldPanel


class BaseFieldQueryPanel(BaseFieldPanel):
    def __init__(self, *args, **kwargs):
        super(BaseFieldQueryPanel, self).__init__(*args, **kwargs)
        target_model = self.bound_field.field.queryset.model
        self.bound_field.field.queryset = target_model.objects.filter(self.query)


class FieldQueryPanel(FieldPanel):
    def __init__(self, field, query, **kwargs):
        super(FieldQueryPanel, self).__init__(field, **kwargs)
        self.query = query

    def bind_to_model(self, model):
        base = {
            'model': model,
            'field_name': self.field_name,
            'classname': self.classname,
            'query': self.query
        }

        if self.widget:
            base['widget'] = self.widget

        return type(str('_FieldQueryPanel'), (BaseFieldQueryPanel,), base)
