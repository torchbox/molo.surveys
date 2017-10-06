(function($) {
    window.SkipLogic = function (opts) {
        var self = {};
        self.container = $('#' + opts.id);

        var validSelectors = ['radio', 'checkbox', 'dropdown', 'checkboxes'];
        var validSkipSelectors = ['radio', 'checkbox', 'dropdown'];
        return function(prefix) {
            var splitPrefix = prefix.split('-');
            var fieldID = [splitPrefix[0], splitPrefix[3]].join('-');
            var parentFieldSelector = $('#id_' + fieldID + '-field_type');
            var choices = $('#' + fieldID + '-skip_logic-list').closest('.skip-logic');

            var skipLogicSelect = $('#' + prefix + '-skip_logic');
            var skipLogicSurvey = $('#' + prefix + '-survey').closest('li');

            var updateBlockState = function () {
                skipLogicSurvey.hide();
                switch (skipLogicSelect.val()) {
                    case 'survey':
                        skipLogicSurvey.show();
                        break;
                    default:
                        break;
                }
            };

            var shouldHide = function () {
                return validSelectors.indexOf(parentFieldSelector.val()) < 0;
            };
            var show = function() {
                choices.show(250);
            };

            var hide = function() {
                choices.hide(250);
            };
            var toggle = function() {
                if (shouldHide()) {
                    hide();
                } else {
                    show();
                    var shouldShowSkipLogic = validSkipSelectors.indexOf(parentFieldSelector.val()) >= 0;
                    if (!shouldShowSkipLogic) {
                        skipLogicSurvey.hide();
                        skipLogicSelect.closest('li').hide();
                    } else {
                        skipLogicSelect.closest('li').show();
                        updateBlockState();
                    }
                }
            };

            toggle();
            updateBlockState();

            parentFieldSelector.change( function () {
                toggle();
            });
            skipLogicSelect.change( function () {
                updateBlockState();
            });
        };
    };
})(jQuery);
