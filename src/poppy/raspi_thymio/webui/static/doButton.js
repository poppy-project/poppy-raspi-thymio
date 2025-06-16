
var resetButtonLabels = function(meta={}) {
    for (const button of document.getElementsByClassName("btn")) {
	if (button.id.substring(0,1) == "N" && Number(button.id.substring(1,2)) > 0) {
	    var label = button.id.substring(1,2);
	    button.innerText = button.textContent = button.title = label;
	}
    }
}

var changeButtonLabels = function(meta={}) {
    if (meta.keys) {
	for (const [key, label] of Object.entries(meta.keys)) {
	    var button = document.getElementById(key);
	    if (button && label != null) {
		if (label.endsWith(".svg") && label in svg_assets) {
		    window.console.info("Set " + button.id + " to SVG label /static/" + label);
		    img = document.createElement('img');
		    img.height = 20;
		    img.src = "/static/" + label;
		    img.alt = button.title = label.replace(/\.svg$/, '')
		    button.innerText = button.textContent = "";
		    button.appendChild(img);
		} else {
		    button.innerText = button.textContent = label;
		}
	    }
	}
    }
}

var doButton = function(buttonId, kind="button", meta={}) {
    var button = document.getElementById(buttonId);

    // Patch in the saved program name for "reload Thymio" button.
    if (kind == "program" && buttonId == "reload") {
	var info = document.getElementById("info");
	if (info && info._program) {
	    buttonId = info._program;
	}
    }

    // API request for button.
    var urlCommand = window.location.href + kind + "/" + buttonId;

    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {
	if (this.readyState == 4 && this.status == 200) {
	    window.console.info(this.responseText);
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
	// Remove "chosen" property from all program buttons.
	for (const p of document.getElementsByClassName("pgm")) {
	    p.classList.remove('chosen');
	}
	// Add "chosen" property to this program button, unless
	// this is the "reload Thymio" button.
	if (! button.classList.contains("power")) {
	    button.classList.add('chosen');
	}
	resetButtonLabels();
	changeButtonLabels(meta);
	// Update info area.
	var info = document.getElementById("info");
	if (info && "info" in meta) {
	    info.innerText = info.textContent = meta.info;
	    info._program = buttonId;
	} else {
	    info.innerText = info.textContent = "";
	}
    }
}
