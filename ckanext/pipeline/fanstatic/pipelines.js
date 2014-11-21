$( document ).ready(function() {
	$( "#pipeline" ).change(function () {
	    var id = "";
	    $( "#pipeline option:checked" ).each(function() {
	      id += $( this ).val();
	    });
	    $(".pipeline-description").removeClass().addClass("hidden");
	    $( "#" + id ).removeClass().addClass("pipeline-description");
	  });
});