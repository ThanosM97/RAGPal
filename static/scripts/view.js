/* 
Implements functions that control document entry deletion.
*/

// Sends POST request to delete entry from the knowledge base
function deleteDoc(documentId) {
    fetch('/view', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'id=' + documentId
    })
        .then(response => {
            if (!response.ok) {
                alert("Document is not in the Knowledge Base.")
            } else {
                // Reload the page or update the document list
                location.reload();
            }

        })
        .catch(error => console.error('Error:', error));
}

// onClick event listener for delete button
$(document).ready(function () {
    $('.delete-btn').on('click', function () {
        var documentId = $(this).attr('id');
        deleteDoc(documentId);
    });
});

// onClick event listener for load more button
$(document).ready(function () {
    $('#load-more-btn').on('click', function () {
        var old_limit = parseInt($("#documents").find("div:last").find("button").attr("id"));
        var new_limit = old_limit + 10;
        window.location.href = "/view?limit=" + new_limit
    });
});