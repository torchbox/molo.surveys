(function($) {
    window.SkipLogic = function (opts) {
        var self = {};
        self.container = $('#' + opts.id);

        var validSelectors = ['radio', 'checkbox', 'dropdown', 'checkboxes'];
        var validSkipSelectors = ['radio', 'checkbox', 'dropdown'];
        return function(prefix) {
            var splitPrefix = prefix.split('-');
            var fieldPrefix = splitPrefix[0];
            var fieldID = [fieldPrefix, splitPrefix[1]].join('-');
            var parentFieldSelector = $('#id_' + fieldID + '-field_type');
            var choices = $('#' + fieldID + '-skip_logic-list').closest('.skip-logic');

            var skipLogicSelect = $('#' + prefix + '-skip_logic');
            var skipLogicSurvey = $('#' + prefix + '-survey');
            var questionWidgetID = '#' + prefix + '-question';
            var questionSelect = $(questionWidgetID + '_1');
            var questionID = $(questionWidgetID + '_0');

            var updateBlockState = function () {
                hideElement(skipLogicSurvey);
                hideElement(questionSelect);
                switch (skipLogicSelect.val()) {
                    case 'survey':
                        showElement(skipLogicSurvey);
                        break;
                    case 'question':
                        showElement(questionSelect);
                        break;
                    default:
                        break;
                }
            };

            var populateQuestions = function () {
                var questionSelector = function(field) {
                    return '[id^="inline_child_' + field + '"]';
                };
                var questions = $(questionSelector(fieldPrefix));
                var thisQuestion = $(questionSelector(fieldID));
                var thisSortOrder = thisQuestion.children('[id$="-ORDER"]').val();
                for (let question of questions) {
                    question = $(question);
                    var id = question.children('[id$="-id"]').val();
                    var sortOrder = question.children('[id$="-ORDER"]').val();
                    var label = question.find('input[id$="-label"]').val();
                    var selected = id == questionID.val() ? 'selected' : '';
                    if (thisSortOrder < sortOrder) {
                        questionSelect.append(`<option value="${id}" ${selected}>${label}</option>`);
                    }
                }
            };

            var hideElement = function(element) {
                element.closest('li').hide();
            };

            var showElement = function(element) {
                element.closest('li').show();
            };

            var shouldHide = function () {
                return validSelectors.indexOf(parentFieldSelector.val()) < 0;
            };

            var showChoices = function() {
                choices.show(250);
            };

            var hideChoices = function() {
                choices.hide(250);
            };
            var toggle = function() {
                if (shouldHide()) {
                    hideChoices();
                } else {
                    showChoices();
                    var shouldShowSkipLogic = validSkipSelectors.indexOf(parentFieldSelector.val()) >= 0;
                    if (!shouldShowSkipLogic) {
                        hideElement(skipLogicSurvey);
                        hideElement(questionSelect);
                        hideElement(skipLogicSelect);
                    } else {
                        showElement(skipLogicSelect);
                        updateBlockState();
                    }
                }
            };

            toggle();
            populateQuestions();

            parentFieldSelector.change( function () {
                toggle();
            });
            skipLogicSelect.change( function () {
                updateBlockState();
            });
        };
    };
})(jQuery);
