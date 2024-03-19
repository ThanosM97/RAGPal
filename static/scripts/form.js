/* 
Implements functions that control form input, its submission
and the update of the DOM to new messages.
*/

// Auto-resize textarea based on content
$('#user-input').on('input', function () {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
});

// Prevent newline when Enter key is pressed
$('#user-input').on('keydown', function (event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        postMessage();
    }
});

// Toggle label when switch is toggled
$('#rag-switch .form-check-input').on('change', function () {
    if (this.checked) {
        $('#rag-switch .form-check-label').text('Enabled')
    } else {
        $('#rag-switch .form-check-label').text('Disabled')
    }
});


function postMessage() {
    var userInput = $('#user-input').val().trim();
    var ragEnabled = $('#switch').is(":checked")
    if (userInput !== '') {
        $('#chat-messages').append('<div class="message user-message">' + userInput + '<span class="from-label">You</span></div>'); // Display user input immediately
        $('#user-input').val(''); // Clear input field
        $('#user-input').css('height', ''); // Reset height to default
        $('#user-input').prop('disabled', true); // Disable input field
        $('#chat-messages').append('<div class="message bot-message">...<span class="from-label">RAGPal</span></div>'); // Add bot message placeholder    

        var socket = new WebSocket("ws://localhost:5000/send_message") // Establish a websocket connection

        socket.onopen = function () {
            var args = JSON.stringify({ prompt: userInput, ragEnabled: ragEnabled })
            socket.send(args)
        };


        socket.onmessage = function (event) {
            if (event.data === "[MESSAGE STARTS HERE]") {
                $('#chat-messages').find('div:last').empty(); // Remove the ... placeholder
            } else if (event.data === "[MESSAGE ENDS HERE]") {
                var markdownText = $('#chat-messages').find('div:last').html() // Get the markdown text

                // Convert Markdown to HTML
                var converter = new showdown.Converter();
                var htmlContent = converter.makeHtml(markdownText);

                // Append the HTML converted context
                $('#chat-messages').find('div:last').html(htmlContent)
                $('#chat-messages').find('div:last').append('<span class="from-label">RAGPal</span>')

                // Enable input field
                $('#user-input').prop('disabled', false);

                // Scroll to the last message
                $('html, body').animate({ scrollTop: $(document).height() }, 'slow');
            } else {
                // Append response chunk to the chat div
                $('#chat-messages').find('div:last').append(event.data)
            }
        }

        socket.onclose = function (event) {
            if (event.code !== 1000) {
                console.log("WebSocket connection closed:", event);
            }
        };
    }
}

// Post message when form is submitted using the button
$(document).ready(function () {
    $('#chat-form').submit(function (event) {
        event.preventDefault();
        postMessage();

    });
});
