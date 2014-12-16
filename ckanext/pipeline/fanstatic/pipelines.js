$( document ).ready(function() {
	$( "#pipeline" ).change(function () {
	    var id = "";
	    $( "#pipeline option:checked" ).each(function() {
	      id += $( this ).val();
	    });
	    $(".pipeline-description").removeClass().addClass("hidden");
	    $( "#" + id ).removeClass().addClass("pipeline-description");
	  });
	
	$("#finish-create-pipe").click(function() {
		window.location = $("#link-show").text();
	});
	
	$(".pipeline-filter").on('input',function(e){
		filter($(".pipeline-filter").val());
	});
});

function filter(filterStr) {
	$("option").each(function() {
		if ($(this).text().toLowerCase().indexOf(filterStr.toLowerCase()) != -1){
			$(this).show();
		} else {
			$(this).hide();
		}
	});
}