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

// Post message when form is submitted using the button
$(document).ready(function () {
    $('#chat-form').submit(function (event) {
        event.preventDefault();
        postMessage();

    });
});

function postMessage() {
    var userInput = $('#user-input').val().trim();
    if (userInput !== '') {
        $('#chat-messages').append('<div class="message user-message">' + userInput + '<span class="from-label">You</span></div>'); // Display user input immediately
        $('#user-input').val(''); // Clear input field
        $('#user-input').css('height', ''); // Reset height to default
        $('#user-input').prop('disabled', true); // Disable input field
        $('#chat-messages').append('<div class="message bot-message">Generating...<span class="from-label">RAGPal</span></div>'); // Add bot message placeholder

        // Send post request to /send_message endpoint
        $.post('/send_message', { "user-input": userInput }, function (response) {
            // Add response to the placeholder
            $('#chat-messages').find('div:last').html(response.bot_response + '<span class="from-label">RAGPal</span></div>')
            $('#user-input').prop('disabled', false); // Enable the input field

            // Scroll to the last message
            $('html, body').animate({ scrollTop: $(document).height() }, 'slow');
        });


    }
}
