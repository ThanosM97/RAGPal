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

        fetch('/send_message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: 'user-input=' + encodeURIComponent(userInput) + "&rag-enabled=" + ragEnabled //for special characters in user's input,
        })
            .then(response => {
                const reader = response.body.getReader();
                let decoder = new TextDecoder();

                $('#chat-messages').find('div:last').empty(); // Remove the ... placeholder

                // Read chunks from the response stream
                reader.read().then(function processResult(result) {
                    var responseChunk = decoder.decode(result.value || new Uint8Array, { stream: true });

                    // Append response chunk to the chat div
                    $('#chat-messages').find('div:last').append(responseChunk)

                    if (result.done) { //Last chunk has arrived, add the span
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

                        return;
                    }

                    // Read the next chunk
                    reader.read().then(processResult);
                });
            })
            .catch(error => {
                // Handle error
                console.error('Error:', error);
            });
    }
}

// Post message when form is submitted using the button
$(document).ready(function () {
    $('#chat-form').submit(function (event) {
        event.preventDefault();
        postMessage();

    });
});
