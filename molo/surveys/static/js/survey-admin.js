$(function(){
  console.log('loaded')
  var multi_step_checkbox = $('#id_multi_step');
  var multi_step_label = $('label[for=id_multi_step]');

  var display_direct_checkbox = $('#id_display_survey_directly');
  var display_direct_label = $('label[for=id_display_survey_directly]');

  var disableMultiStep = function(){
    multi_step_checkbox.attr("disabled", true);
    multi_step_label.css('color', 'lightgray');
  }

  var enableMultiStep = function(){
    multi_step_checkbox.attr("disabled", false);
    multi_step_label.css('color', '#333');
  }

  var disableDisplayDirect = function(){
    display_direct_checkbox.attr("disabled", true);
    display_direct_label.css('color', 'lightgray');
  }

  var enableDisplayDirect = function(){
    display_direct_checkbox.attr("disabled", false);
    display_direct_label.css('color', '#333');
  }

  if (multi_step_checkbox.is(':checked')) {
      disableDisplayDirect();
  }
  else if (display_direct_checkbox.is(':checked')) {
      disableMultiStep();
  }

  display_direct_checkbox.change(
    function(){
        if ($(this).is(':checked')) {
            disableMultiStep();
        }
        else {
          enableMultiStep();
        }
    });

  multi_step_checkbox.change(
    function(){
        if ($(this).is(':checked')) {
          disableDisplayDirect();
        }
        else {
          enableDisplayDirect();
        }
    });
})
