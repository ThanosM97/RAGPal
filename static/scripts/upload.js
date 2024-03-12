/* 
Implements functions that control form input and the automatic 
disappearance of the alert after a form submission.
*/

// Make alert disappear after 4 seconds.
$("#upload-alert").fadeTo(4000, 500).slideUp(500);

// Disable the upload document option when the user writes in the
// text area, and vice versa. Enable upload button only when there
// input to the form.
$(document).ready(function () {
    $('#files').change(function () {
        if ($('#files')[0].files.length !== 0) {
            $('#submit-button').prop('disabled', false);
            $('#text').prop('disabled', true);
        } else {
            $('#text').prop('disabled', false);
            $('#submit-button').prop('disabled', true);
        }
    });

    $('#text').on('input', function () {
        if ($('#text').val() !== '') {
            $('#files').prop('disabled', true);
            $('#submit-button').prop('disabled', false);
        } else {
            $('#files').prop('disabled', false);
            $('#submit-button').prop('disabled', true);
        }

    });
});