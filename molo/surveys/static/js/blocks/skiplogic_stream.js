(function($) {
    window.SkipLogicStreamBlock = function(opts) {
        var initializer = StreamBlock(opts);
        var validSelectors = ['radio', 'checkbox', 'dropdown', 'checkboxes'];
        return function(elementPrefix) {
            initializer(elementPrefix);
            var splitPrefix = elementPrefix.split('-');
            var fieldID = splitPrefix[0] + '-' + splitPrefix[1];
            var parentFieldSelector = $('#id_' + fieldID + '-field_type');
            var choices = $('#' + fieldID + '-skip_logic-list').closest('.skip-logic');

            var toggle = function(duration) {
                if (shouldHide()) {
                    hideChoices(duration);
                } else {
                    showChoices(duration);
                };
            };

            var shouldHide = function () {
                return validSelectors.indexOf(parentFieldSelector.val()) < 0;
            };


            var showChoices = function(duration) {
                choices.show(duration);
            };

            var hideChoices = function(duration) {
                choices.hide(duration);
            };

            toggle(0);

            parentFieldSelector.change( function () {
                toggle(250);
            });
        };
    };
})(jQuery);
