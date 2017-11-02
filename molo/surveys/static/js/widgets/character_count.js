(function() {
    document.addEventListener('DOMContentLoaded', function() {
        var inputs = document.querySelectorAll('.input-group input[type="text"]');
        var setSpanValue = function(target, span) {
            var limit = parseInt(target.getAttribute('maxlength'));
            var current = target.value.length;
            var remaining = limit - current;
            span.textContent = remaining;
        };
        for (var i = 0; i < inputs.length; i++) {
            var span = document.createElement('span');
            inputs[i].parentNode.insertBefore(span, inputs[i].nextSibling);
            setSpanValue(inputs[i], span);
            inputs[i].addEventListener("input", function(e) {
                var span = e.target.nextSibling;
                setSpanValue(e.target, span);
            },false);
        }
    }, false);
})();
