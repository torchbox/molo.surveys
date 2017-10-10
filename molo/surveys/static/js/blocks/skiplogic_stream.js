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

            var questionSelector = function(field) {
                return '[id^="inline_child_' + field + '"]';
            };
            var thisQuestion = $(questionSelector(fieldID));

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

            var wrapAction = function (element, cb) {
                var nativeEvent = $._data(element[0], 'events');

                var opts = {};
                opts.question = thisQuestion;
                opts.nativeHandler = nativeEvent.click[0].handler;
                element.unbind('click', opts.nativeHandler);
                element.click(function(event) {
                    var allQuestions = $(questionSelector(splitPrefix[0]));
                    var shouldEnd = false;
                    for (let question of allQuestions) {
                        if (!shouldEnd && $(question) !== thisQuestion) {
                            shouldEnd = cb.bind(opts)(event, $(question));
                        }
                    }
                });
            };

            thisQuestion.find('[id$="-label"]').change( function(event) {
                var sortOrder = parseInt(thisQuestion.children('[id$="-ORDER"]').val());
                var questionSelectors = $('[id$="-question_1"]');
                questionSelectors.find(`option[value=${sortOrder}]`).text(event.target.value);
            });
            var swapSortOrder = function (from, to) {
                var questionSelectors = $('[id$="-question_1"]');
                var fromSelectors = questionSelectors.find(`option[value=${from}]`);
                var toSelectors = questionSelectors.find(`option[value=${to}]`);
                fromSelectors.val(to);
                toSelectors.val(from);
            };

            // If this is a new element it wont have any questions to link to so dont need to handle logic
            if (thisQuestion.children('[id$="-ORDER"]').val()) {
                var questionUp = thisQuestion.find('[id$="-move-up"]');
                var questionDown = thisQuestion.find('[id$="-move-down"]');
                var questionDelete = thisQuestion.find('[id$="-DELETE-button"]');

                wrapAction(questionDelete, function(event, question) {
                    var id = this.question.children('[id$="-id"]').val();
                    var sortOrder = parseInt(this.question.children('[id$="-ORDER"]').val());
                    var questionSelectors = question.find('[id$="-question_1"]');
                    var questionLabel = question.find('[id$="-label"]').val();
                    if ( questionSelectors.filter(':visible').is( function(index, element) {
                        return $(element).val() == sortOrder;
                    } )) {
                        alert(`Cannot delete, referenced by skip logic in question "${questionLabel}".`);
                        return true;
                    } else {
                        this.nativeHandler(event);
                        questionSelectors.find(`option[value=${sortOrder}]`).remove();
                    }
                });
                wrapAction(questionUp, function(event, question) {
                    var id = this.question.children('[id$="-id"]').val();
                    var sortOrder = parseInt(this.question.children('[id$="-ORDER"]').val());
                    var targetSortOrder = parseInt(question.children('[id$="-ORDER"]').val());
                    var questionSelectors = question.find('[id$="-question_1"]');
                    var questionLabel = question.find('[id$="-label"]').val();
                    if ( targetSortOrder + 1 == sortOrder) {
                        if ( questionSelectors.filter(':visible').is( function(index, element) {
                            return $(element).val() == sortOrder;
                        } )) {
                            alert(`Cannot move above "${questionLabel}", please change the logic.`);
                            return true;
                        } else {
                            questionSelectors.find(`option[value=${sortOrder}]`).remove();
                            this.nativeHandler(event);
                            swapSortOrder(sortOrder, targetSortOrder);
                            return true;
                        }
                    }
                });
                wrapAction(questionDown, function(event, question) {
                    var id = this.question.children('[id$="-id"]').val();
                    var thisQuestionSelectors = this.question.find('[id$="-question_1"]');
                    var sortOrder = parseInt(this.question.children('[id$="-ORDER"]').val());
                    var targetSortOrder = parseInt(question.children('[id$="-ORDER"]').val());
                    var targetID = question.children('[id$="-id"]').val();
                    var questionSelectors = question.find('[id$="-question_1"]');
                    var questionLabel = question.find('[id$="-label"]').val();
                    if ( targetSortOrder - 1 == sortOrder) {
                        if ( thisQuestionSelectors.filter(':visible').is( function(index, element) {
                            return $(element).val() == targetSortOrder;
                        } )) {
                            alert(`Cannot move below "${questionLabel}", please change the logic.`);
                            return true;
                        } else {
                            thisQuestionSelectors.find(`option[value=${targetSortOrder}]`).remove();
                            this.nativeHandler(event);
                            swapSortOrder(sortOrder, targetSortOrder);
                            var label = this.question.find('input[id$="-label"]').val();
                            questionSelectors.prepend(
                                `<option value="${sortOrder}">${label}</option>`
                            );
                            return true;
                        }
                    }
                });
            }
        };
    };
})(jQuery);
