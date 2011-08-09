var initialized = false;

function update_output() {
    data = {}
    data.data = $('#id_data').val();
    data.format = 'json';
    if ( $('#id_remove_comments').attr('checked') ) {
	data.remove_comments = 1
    }
    if ( $('#id_highlight').attr('checked') ) { data.highlight = 1 }
    data.keyword_case = $('#id_keyword_case').val();
    data.identifier_case = $('#id_identifier_case').val();
    data.n_indents = $('#id_n_indents').val();
    data.output_format = $('#id_output_format').val();
    form = document.getElementById('form_options');
    $(form.elements).attr('disabled', 'disabled');
    $('#response').addClass('loading');
    $.post('/', data,
	function(data) {
	    if ( data.output )  {
		$('#response').html(data.output);
		proc_time = 'Processed in '+data.proc_time+' seconds.';
	    } else {
		$('#response').html('An error occured: '+data.errors);
		proc_time = '';
	    }
	    $('#proc_time').html(proc_time);
	    $(form.elements).each( function(idx) {
		    obj = $(this);
		    if ( ! obj.is('.keep-disabled') ) {
			obj.removeAttr('disabled');
		    }
		});
	    $('#response').removeClass('loading');
	}, 'json');
    return false;
}

function toggle_fieldset(event) {
    id = $(this).attr('id');
    $('#'+id+'_content').slideDown();
    $('legend').each(function(idx) {
	    obj = $('#'+this.id+'_content');
	    if ( this.id != id ) {
		obj.slideUp();
	    }
	});
}


function textarea_grab_focus(evt) {
    evt.stopPropagation();
    evt.preventDefault();
    $('#id_data').focus();
    return false;
}


function show_help() {
    $('#help').toggle();
    return false;
}


function hide_help() {
    $('#help').hide();
    return false;
}

function load_example() {
    fname = $('#sel_example').val();
    data = {fname: fname};
    $.post('/load_example', data,
	       function(data) {
	       $('#id_data').val(data.answer);
	   }, 'json');
}


function init() {
    if (initialized) { return }
    //$('legend').bind('click', toggle_fieldset);
    //    $('legend').each(function(idx) {
    //	    obj = $('#'+this.id+'_content');
    //	    if ( this.id != 'general' ) {
    //		obj.hide();
    //	    }
    //	});
    $(document).bind('keydown', {combi:'Ctrl+f'},
		     update_output);
    $('#btn_format').val('Format SQL [Ctrl+F]');
    $(document).bind('keydown', {combi: 'h', disableInInput: true},
		     show_help);
    $(document).bind('keydown', 'Esc', hide_help);
    $(document).bind('keydown', {combi: 't', disableInInput: true},
		     textarea_grab_focus);
    initialized = true;
}