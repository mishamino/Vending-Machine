document.querySelectorAll('.delete-form').forEach((form) => {
    form.addEventListener('submit', (event) => {
        if (!window.confirm('Delete this product? Historical transaction records will be preserved.')) {
            event.preventDefault();
        }
    });
});
