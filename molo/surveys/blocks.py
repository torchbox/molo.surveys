from django import forms
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.core.exceptions import ValidationError

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
        args = [SkipLogicStreamBlock([('skip_logic', SkipLogicBlock())])]
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


class SelectAndHiddenWidget(forms.MultiWidget):
    def __init__(self, *args, **kwargs):
        widgets = [forms.HiddenInput, forms.Select]
        super(SelectAndHiddenWidget, self).__init__(
            widgets=widgets,
            *args,
            **kwargs
        )

    def decompress(self, value):
        return [value, None]

    def value_from_datadict(self, *args):
        value = super(SelectAndHiddenWidget, self).value_from_datadict(*args)
        return value[1]


class SkipLogicStreamBlock(blocks.StreamBlock):
    @property
    def media(self):
        media = super(SkipLogicStreamBlock, self).media
        media.add_js(
            [static('js/blocks/skiplogic_stream.js')]
        )
        media.add_css(
            {'all': [static('css/blocks/skiplogic.css')]}
        )
        return media

    def js_initializer(self):
        init = super(SkipLogicStreamBlock, self).js_initializer()
        return 'SkipLogic' + init


class QuestionSelectBlock(blocks.IntegerBlock):
    def __init__(self, *args, **kwargs):
        super(QuestionSelectBlock, self).__init__(*args, **kwargs)
        self.field.widget = SelectAndHiddenWidget()


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
    survey = blocks.PageChooserBlock(
        target_model='surveys.MoloSurveyPage',
        required=False,
    )
    question = QuestionSelectBlock(
        required=False,
        help_text=('Please save the survey as a draft to populate or update '
                   'the list of questions.'),
    )

    @property
    def media(self):
        return forms.Media(js=[static('js/blocks/skiplogic.js')])

    def js_initializer(self):
        opts = {'validSkipSelectors': ['radio', 'checkbox', 'dropdown']}
        return "SkipLogic(%s)" % blocks.utils.js_dict(opts)

    def clean(self, value):
        cleaned_data = super(SkipLogicBlock, self).clean(value)
        logic = cleaned_data['skip_logic']
        if logic == SkipState.SURVEY:
            if not cleaned_data['survey']:
                raise ValidationError(
                    'A Survey must be selected to progress to.',
                    params={'survey': ['Please select a survey.']}
                )
            cleaned_data['question'] = None

        if logic == SkipState.QUESTION:
            if not cleaned_data['question']:
                raise ValidationError(
                    'A Question must be selected to progress to.',
                    params={'question': ['Please select a question.']}
                )
            cleaned_data['survey'] = None

        if logic in [SkipState.END, SkipState.NEXT]:
            cleaned_data['survey'] = None
            cleaned_data['question'] = None

        return cleaned_data
