var doButton = function(buttonId, kind="button") {
    var button = document.getElementById(buttonId);
    var urlCommand = window.location.href + kind + "/" + buttonId;

    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {
	if (this.readyState == 4 && this.status == 200) {
	    document.getElementById("console").innerHTML = this.responseText;
	}
    };

    // Button debounce: disable the button while handling the request.
    var buttonState = function(opacity=1.0, disabled=false) {
	button.style.opacity = opacity;
	button.disabled = disabled;
    }

    buttonState(0.4, true);
    xhttp.open("GET", urlCommand, true);
    xhttp.send();

    // Reenable the button after debounce delay 200 ms.
    setTimeout(buttonState, 200);

    // Program buttons highlight last chosen.
    if (kind == "program") {
	// $('button').removeClass('chosen');
	for (const p of document.getElementsByClassName("pgm")) {
	    p.classList.remove('chosen');
	}
	button.classList.add('chosen');
    }
}
