from wagtail.wagtailadmin.edit_handlers import StreamFieldPanel
from wagtail.wagtailcore import blocks


class SkipLogicStreamPanel(StreamFieldPanel):
    def bind_to_model(self, model):
        model_class = super(SkipLogicStreamPanel, self).bind_to_model(model)
        model_class.classname = 'skip-logic'
        return model_class


class SkipLogicBlock(blocks.StructBlock):
    choice = blocks.CharBlock()
    skip_logic = blocks.ChoiceBlock(
        choices=[
            ('next', 'Next default question'),
            ('end', 'End of survey'),
            ('another', 'Another survey'),
        ],
        default='next',
        required=True,
    )
