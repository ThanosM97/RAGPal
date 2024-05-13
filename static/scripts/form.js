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

// Function to save message history to localStorage
function saveMessageHistory(messages) {
    localStorage.setItem('messageHistory', JSON.stringify(messages));
}

// Function to retrieve message history from localStorage
function getMessageHistory() {
    var messageHistory = localStorage.getItem('messageHistory');
    return messageHistory ? JSON.parse(messageHistory) : [];
}

// Function to append a new message to the conversation history and save it to localStorage
function appendMessageAndSave(message) {
    var messageHistory = getMessageHistory();
    messageHistory.push(message);
    saveMessageHistory(messageHistory);
}

// Function to pass only the last n items of messageHistory
function getLastNItems(messageHistory, n) {
    const startIndex = Math.max(0, messageHistory.length - n); // Calculate the start index
    return messageHistory.slice(startIndex);
}



function postMessage() {
    var userInput = $('#user-input').val().trim();
    var ragEnabled = $('#switch').is(":checked")
    if (userInput !== '') {
        $('#chat-messages').append('<div class="message user-message">' + userInput + '<span class="from-label">You</span></div>'); // Display user input immediately
        $('#user-input').val(''); // Clear input field
        $('#user-input').css('height', ''); // Reset height to default
        $('#user-input').prop('disabled', true); // Disable input field
        $('#chat-messages').append('<div class="message bot-message"></div>'); // Add bot message placeholder    

        var socket = new WebSocket("ws://localhost:5000/send_message") // Establish a websocket connection

        socket.onopen = function () {
            var messageHistory = getLastNItems(getMessageHistory(), 10);
            var args = JSON.stringify({ prompt: userInput, ragEnabled: ragEnabled, history: messageHistory })
            socket.send(args)
        };


        socket.onmessage = function (event) {
            // Append response chunk to the chat div
            const eventData = JSON.parse(event.data);
            $('#chat-messages').find('div:last').append(eventData.text)
        }

        socket.onclose = function (event) {
            if (event.code !== 1000) {
                console.log("WebSocket connection closed:", event);
            } else {
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

                // Save query and response to cache
                const newQeury = { role: 'user', content: userInput };
                appendMessageAndSave(newQeury);

                const newResponse = { role: 'assistant', content: markdownText };
                appendMessageAndSave(newResponse);
            }
        };
    }
}

// Function to clear cache on page refresh
function clearCacheOnRefresh() {
    localStorage.removeItem('messageHistory');
}

// Post message when form is submitted using the button
$(document).ready(function () {
    $('#chat-form').submit(function (event) {
        event.preventDefault();
        postMessage();
    });
    clearCacheOnRefresh();
});
