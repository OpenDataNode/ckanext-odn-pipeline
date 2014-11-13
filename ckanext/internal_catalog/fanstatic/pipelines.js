$( document ).ready(function() {
	console.log('doc ready');
	$( "#pipeline" ).change(function () {
		console.log("changed pipeline selection");
	    var id = "";
	    $( "#pipeline option:checked" ).each(function() {
	      id += $( this ).val();
	    });
	    console.log('checked ' + id);
	    $(".pipeline-description").removeClass().addClass("hidden");
	    $( "#" + id ).removeClass().addClass("pipeline-description");
	    console.log('toggled classes');
	  });
});