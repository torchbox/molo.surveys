(function($) {
    window.SkipLogic = function (opts) {
        var validSkipSelectors = opts['validSkipSelectors'];
        return function(prefix) {
            var splitPrefix = prefix.split('-');
            var fieldPrefix = splitPrefix[0];
            var fieldID = [fieldPrefix, splitPrefix[1]].join('-');

            var skipLogicSelect = $('#' + prefix + '-skip_logic');
            var skipLogicSurvey = $('#' + prefix + '-survey');
            var skipLogicChoice = $('#' + prefix + '-choice');
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
                    var sortOrder = question.sortOrder();
                    var label = question.label().val();
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
                    showElement(skipLogicChoice);
                } else if (thisQuestion.fieldSelect().val() == 'checkbox') {
                    showElement(questionSelect);
                    hideElement(skipLogicChoice);
                    updateBlockState();
                } else {
                    showElement(skipLogicChoice);
                    showElement(skipLogicSelect);
                    updateBlockState();
                }
            };

            toggle();
            populateQuestions();

            skipLogicSelect.change( function () {
                updateBlockState();
            });
            thisQuestion.fieldSelect().change( function () {
                toggle();
            });
        };
    };
})(jQuery);
