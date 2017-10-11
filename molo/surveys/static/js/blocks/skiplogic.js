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

            var thisQuestion = question(fieldID);

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
                for (let question of allQuestions(fieldPrefix)) {
                    question = $(question);
                    var sortOrder = parseInt(question.children('[id$="-ORDER"]').val());
                    var label = question.find('input[id$="-label"]').val();
                    var selected = sortOrder == questionID.val() ? 'selected' : '';
                    if (thisQuestion.sortOrder() < sortOrder) {
                        questionSelect.append(
                            `<option value="${sortOrder}" ${selected}>${label}</option>`
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
                var shouldShowSkipLogic = validSkipSelectors.indexOf(thisQuestion.fieldSelect().val()) >= 0;
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
        };
    };
})(jQuery);
