(function($) {
    window.SkipLogic = function (opts) {
        var self = {};
        self.container = $('#' + opts.id);

        var validSelectors = ['radio', 'checkbox', 'dropdown'];
        return function(prefix) {
            var selectorID = prefix.slice(0, prefix.indexOf('-', prefix.indexOf('-') + 1));
            var parentFieldSelector = $('#id_' + selectorID + '-field_type');
            var choices = $('#' + selectorID + '-skip_logic-list').closest('.skip-logic');
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
                }
            };
            toggle();
            parentFieldSelector.change( function () {
                toggle();
            });
        };
    }
})(jQuery);
