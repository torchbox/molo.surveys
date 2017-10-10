(function($) {
    window.SkipLogic = function (opts) {
        var validSkipSelectors = opts['validSkipSelectors'];
        return function(prefix) {
            var splitPrefix = prefix.split('-');
            var fieldPrefix = splitPrefix[0];
            var fieldID = [fieldPrefix, splitPrefix[1]].join('-');
            var parentFieldSelector = $('#id_' + fieldID + '-field_type');
            var parentFieldLabel = $('#id_' + fieldID + '-label');

            var skipLogicSelect = $('#' + prefix + '-skip_logic');
            var skipLogicSurvey = $('#' + prefix + '-survey');
            var questionWidgetID = '#' + prefix + '-question';
            var questionSelect = $(questionWidgetID + '_1');
            var questionID = $(questionWidgetID + '_0');

            var questionSelector = function(field) {
                return '[id^="inline_child_' + field + '"]';
            };
            var thisQuestion = $(questionSelector(fieldID));
            var thisSortOrder = thisQuestion.children('[id$="-ORDER"]').val();
            var allQuestions = $(questionSelector(fieldPrefix));

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
                for (let question of allQuestions) {
                    question = $(question);
                    var id = question.children('[id$="-id"]').val();
                    var sortOrder = question.children('[id$="-ORDER"]').val();
                    var label = question.find('input[id$="-label"]').val();
                    var selected = id == questionID.val() ? 'selected' : '';
                    if (thisSortOrder < sortOrder) {
                        questionSelect.append(
                            `<option data-sortorder="${sortOrder}" value="${id}" ${selected}>${label}</option>`
                        );
                    }
                }
            };

            var hideElement = function(element) {
                element.closest('li').hide();
            };

            var showElement = function(element) {
                element.closest('li').show();
            };

            var toggle = function() {
                var shouldShowSkipLogic = validSkipSelectors.indexOf(parentFieldSelector.val()) >= 0;
                if (!shouldShowSkipLogic) {
                    hideElement(skipLogicSurvey);
                    hideElement(questionSelect);
                    hideElement(skipLogicSelect);
                } else {
                    showElement(skipLogicSelect);
                    updateBlockState();
                }
            };

            toggle();
            populateQuestions();

            skipLogicSelect.change( function () {
                updateBlockState();
            });
            parentFieldSelector.change( function () {
                toggle();
            });

            for (let question of allQuestions) {
                var $question = $(question);
                var questionUp = $question.find('[id$="-move-up"]');
                var questionDown = $question.find('[id$="-move-down"]');
                var questionDelete = $question.find('[id$="-DELETE-button"]');
                var nativeEvent = $._data(questionDelete[0], 'events');

                opts = {};
                opts.question = $question;
                opts.nativeHandler = nativeEvent.click[0].handler;

                questionDelete.unbind('click', opts.nativeHandler);

                questionDelete.click( function(event) {
                    var id = this.question.children('[id$="-id"]').val();
                    if ( questionSelect.val() != id ) {
                        this.nativeHandler(event);
                        questionSelect.find(`option[value=${id}]`).remove();
                    } else {
                        alert(`Cannot delete, referenced by skip logic in question "${parentFieldLabel.val()}".`);
                    }
                }.bind(opts));

            };
        };
    };
})(jQuery);
