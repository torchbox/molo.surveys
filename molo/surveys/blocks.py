from django import forms
from django.contrib.staticfiles.templatetags.staticfiles import static

from wagtail.wagtailadmin.edit_handlers import StreamFieldPanel
from wagtail.wagtailcore import blocks
from wagtail.wagtailcore.fields import StreamField


class SkipState:
    NEXT = 'next'
    END = 'end'
    QUESTION = 'question'
    SURVEY = 'survey'


class SkipLogicField(StreamField):
    def __init__(self, *args, **kwargs):
        args = [[('skip_logic', SkipLogicBlock())]]
        kwargs.update({
            'verbose_name': 'Answer options',
            'blank': True,
        })
        super(SkipLogicField, self).__init__(*args, **kwargs)


class SkipLogicStreamPanel(StreamFieldPanel):
    def bind_to_model(self, model):
        model_class = super(SkipLogicStreamPanel, self).bind_to_model(model)
        model_class.classname = 'skip-logic'
        return model_class


class SkipLogicBlock(blocks.StructBlock):
    choice = blocks.CharBlock()
    skip_logic = blocks.ChoiceBlock(
        choices=[
            (SkipState.NEXT, 'Next default question'),
            (SkipState.END, 'End of survey'),
            (SkipState.QUESTION, 'Another question'),
            (SkipState.SURVEY, 'Another survey'),
        ],
        default=SkipState.NEXT,
        required=True,
    )
    survey = blocks.PageChooserBlock(target_model='surveys.MoloSurveyPage', required=False)


    @property
    def media(self):
        return forms.Media(js=[static('js/blocks/skiplogic.js')])

    def js_initializer(self):
        opts = {}
        return "SkipLogic(%s)" % blocks.utils.js_dict(opts)
