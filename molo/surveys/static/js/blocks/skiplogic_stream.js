(function($) {
    var questionSelector = function(field) {
        return '[id^="inline_child_' + field + '"]';
    };

    var addHelperMethods = function (question) {
        question.choices = () => question.find('[id$="-skip_logic-list"]').closest('.skip-logic');
        question.fieldSelect = () => question.find('[id$="-field_type"]');
        question.sortOrder = () => parseInt(question.children('[id$="-ORDER"]').val());
        question.quesiontID = () => question.children('[id$="-id"]').val();
        question.label = () => question.find('input[id$="-label"]');
        question.questionSelectors = () => question.find('[id$="-question_1"]');
        return question;
    };

    window.question = function(id) {
        this.fieldID = id;
        var thisQuestion = $(questionSelector(this.fieldID));
        return addHelperMethods(thisQuestion);
    };

    window.allQuestions = function(id) {
        var allQuestions = $(questionSelector(id));
        allQuestions = allQuestions.map(addHelperMethods);
        return allQuestions;
    };

    window.SkipLogicStreamBlock = function(opts) {
        var initializer = StreamBlock(opts);
        var validSelectors = ['radio', 'checkbox', 'dropdown', 'checkboxes'];
        return function(elementPrefix) {
            initializer(elementPrefix);
            var splitPrefix = elementPrefix.split('-');
            var fieldID = splitPrefix[0] + '-' + splitPrefix[1];
            var thisQuestion = question(fieldID);

            var allQuestionSelectors = () => $('[id$="-question_1"]');

            var toggle = function(duration) {
                if (shouldHide()) {
                    hideChoices(duration);
                } else {
                    showChoices(duration);
                };
            };

            var shouldHide = function () {
                return validSelectors.indexOf(thisQuestion.fieldSelect().val()) < 0;
            };

            var showChoices = function(duration) {
                thisQuestion.choices().show(duration);
            };

            var hideChoices = function(duration) {
                thisQuestion.choices().hide(duration);
            };

            toggle(0);

            thisQuestion.fieldSelect().change( function () {
                toggle(250);
            });

            var wrapAction = function (element, cb) {
                var nativeEvent = $._data(element[0], 'events');

                var opts = {};
                opts.question = thisQuestion;
                opts.nativeHandler = nativeEvent.click[0].handler;
                element.unbind('click', opts.nativeHandler);
                element.click(function(event) {
                    var shouldEnd = false;
                    for (let question of allQuestions(splitPrefix[0])) {
                        if (!shouldEnd && $(question) !== thisQuestion) {
                            shouldEnd = cb.bind(opts)(event, $(question));
                        }
                    }
                });
            };

            thisQuestion.label().change( function(event) {
                var sortOrder = thisQuestion.sortOrder();
                allQuestionSelectors().find(`option[value=${sortOrder}]`).text(event.target.value);
            });

            var swapSortOrder = function (from, to) {
                var fromSelectors = allQuestionSelectors().find(`option[value=${from}]`);
                var toSelectors = allQuestionSelectors().find(`option[value=${to}]`);
                fromSelectors.val(to);
                toSelectors.val(from);
            };

            // If this is a new element it wont have any questions to link to so dont need to handle logic
            if (thisQuestion.sortOrder()) {
                var questionUp = thisQuestion.find('[id$="-move-up"]');
                var questionDown = thisQuestion.find('[id$="-move-down"]');
                var questionDelete = thisQuestion.find('[id$="-DELETE-button"]');

                wrapAction(questionDelete, function(event, question) {
                    var sortOrder = thisQuestion.sortOrder();
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
                    var sortOrder = thisQuestion.sortOrder();
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
                    var thisQuestionSelectors = thisQuestion.questionSelectors();
                    var sortOrder = thisQuestion.sortOrder();
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
                            var label = thisQuestion.label().val();
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
