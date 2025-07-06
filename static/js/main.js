// Recipe Manager - Main JavaScript

// DOM Ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize auto-hiding alerts
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Recipe search autocomplete
    initializeSearchAutocomplete();
    
    // Recipe scaling functionality
    initializeRecipeScaling();
    
    // Shopping list functionality
    initializeShoppingList();
    
    // Meal planning drag and drop
    initializeMealPlanning();
});

// Search Autocomplete
function initializeSearchAutocomplete() {
    const searchInput = document.querySelector('input[name="q"]');
    if (!searchInput) return;
    
    let searchTimeout;
    const resultsContainer = document.createElement('div');
    resultsContainer.className = 'search-results position-absolute bg-white border rounded shadow-sm';
    resultsContainer.style.cssText = 'top: 100%; left: 0; right: 0; z-index: 1000; max-height: 300px; overflow-y: auto; display: none;';
    
    searchInput.parentNode.style.position = 'relative';
    searchInput.parentNode.appendChild(resultsContainer);
    
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();
        
        if (query.length < 2) {
            resultsContainer.style.display = 'none';
            return;
        }
        
        searchTimeout = setTimeout(() => {
            fetch(`/recipes/api/search/?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    displaySearchResults(data.results, resultsContainer);
                })
                .catch(error => console.error('Search error:', error));
        }, 300);
    });
    
    // Hide results when clicking outside
    document.addEventListener('click', function(e) {
        if (!searchInput.parentNode.contains(e.target)) {
            resultsContainer.style.display = 'none';
        }
    });
}

function displaySearchResults(results, container) {
    if (results.length === 0) {
        container.style.display = 'none';
        return;
    }
    
    container.innerHTML = results.map(result => `
        <a href="${result.url}" class="d-flex align-items-center p-2 text-decoration-none border-bottom">
            ${result.image ? `<img src="${result.image}" class="rounded me-2" style="width: 40px; height: 40px; object-fit: cover;">` : '<div class="bg-light rounded me-2 d-flex align-items-center justify-content-center" style="width: 40px; height: 40px;"><i class="bi bi-image text-muted"></i></div>'}
            <span class="text-dark">${result.title}</span>
        </a>
    `).join('');
    
    container.style.display = 'block';
}

// Recipe Scaling
function initializeRecipeScaling() {
    const scalingControls = document.querySelector('.recipe-scaling');
    if (!scalingControls) return;
    
    const servingsInput = scalingControls.querySelector('input[name="servings"]');
    const originalServings = parseInt(servingsInput.dataset.original || servingsInput.value);
    
    servingsInput.addEventListener('change', function() {
        const newServings = parseInt(this.value);
        const multiplier = newServings / originalServings;
        
        // Update all ingredient quantities
        document.querySelectorAll('.ingredient-quantity').forEach(element => {
            const originalQuantity = parseFloat(element.dataset.original || element.textContent);
            const newQuantity = (originalQuantity * multiplier).toFixed(2);
            element.textContent = parseFloat(newQuantity); // Remove trailing zeros
            element.dataset.original = originalQuantity;
        });
    });
}

// Shopping List Functionality
function initializeShoppingList() {
    // Auto-save item completion status
    document.querySelectorAll('.shopping-item input[type="checkbox"]').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const itemId = this.closest('.shopping-item').dataset.itemId;
            updateShoppingItemStatus(itemId, this.checked);
        });
    });
    
    // Bulk actions
    const selectAllCheckbox = document.querySelector('#select-all-items');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            const checkboxes = document.querySelectorAll('.shopping-item input[type="checkbox"]');
            checkboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
                const itemId = checkbox.closest('.shopping-item').dataset.itemId;
                updateShoppingItemStatus(itemId, this.checked);
            });
        });
    }
}

function updateShoppingItemStatus(itemId, completed) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    fetch(`/shopping/item/${itemId}/toggle/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `completed=${completed}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update visual feedback
            const item = document.querySelector(`[data-item-id="${itemId}"]`);
            if (completed) {
                item.classList.add('completed');
            } else {
                item.classList.remove('completed');
            }
            
            // Update progress if element exists
            const progressBar = document.querySelector('.progress-bar');
            if (progressBar && data.completion_percentage !== undefined) {
                progressBar.style.width = data.completion_percentage + '%';
            }
        }
    })
    .catch(error => console.error('Error updating item:', error));
}

// Meal Planning Functionality
function initializeMealPlanning() {
    // Quick add meal functionality
    const addMealButtons = document.querySelectorAll('.add-meal-btn');
    addMealButtons.forEach(button => {
        button.addEventListener('click', function() {
            const date = this.dataset.date;
            const mealType = this.dataset.mealType;
            showQuickAddMealDialog(date, mealType);
        });
    });
    
    // Meal completion toggle
    document.querySelectorAll('.meal-item').forEach(item => {
        item.addEventListener('dblclick', function() {
            const mealId = this.dataset.mealId;
            toggleMealCompletion(mealId);
        });
    });
}

function showQuickAddMealDialog(date, mealType) {
    // Create and show a simple modal for quick meal addition
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Add ${mealType} for ${date}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form class="quick-add-meal-form">
                    <div class="modal-body">
                        <input type="hidden" name="date" value="${date}">
                        <input type="hidden" name="meal_type" value="${mealType}">
                        <div class="mb-3">
                            <label class="form-label">Recipe</label>
                            <select name="recipe" class="form-select" required>
                                <option value="">Select a recipe...</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Servings</label>
                            <input type="number" name="servings" class="form-control" value="1" min="1" required>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="submit" class="btn btn-primary">Add Meal</button>
                    </div>
                </form>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
    
    // Load recipes for the select
    loadUserRecipes(modal.querySelector('select[name="recipe"]'));
    
    // Handle form submission
    modal.querySelector('.quick-add-meal-form').addEventListener('submit', function(e) {
        e.preventDefault();
        addMealPlan(new FormData(this), bsModal);
    });
    
    // Clean up when modal is hidden
    modal.addEventListener('hidden.bs.modal', function() {
        document.body.removeChild(modal);
    });
}

function loadUserRecipes(selectElement) {
    fetch('/recipes/api/my-recipes/')
        .then(response => response.json())
        .then(data => {
            selectElement.innerHTML = '<option value="">Select a recipe...</option>' +
                data.recipes.map(recipe => `<option value="${recipe.id}">${recipe.title}</option>`).join('');
        })
        .catch(error => console.error('Error loading recipes:', error));
}

function addMealPlan(formData, modal) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    fetch('/meal-planning/add/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            modal.hide();
            location.reload(); // Reload to show the new meal
        } else {
            alert('Error adding meal: ' + JSON.stringify(data.errors));
        }
    })
    .catch(error => {
        console.error('Error adding meal:', error);
        alert('Error adding meal. Please try again.');
    });
}

// Utility Functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatTime(minutes) {
    if (minutes < 60) {
        return `${minutes}m`;
    }
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}

// Recipe rating stars interaction
function initializeRatingStars() {
    const ratingStars = document.querySelectorAll('.rating-input .bi-star');
    ratingStars.forEach((star, index) => {
        star.addEventListener('click', function() {
            const rating = index + 1;
            const container = this.closest('.rating-input');
            const hiddenInput = container.querySelector('input[type="hidden"]');
            hiddenInput.value = rating;
            
            // Update star display
            const allStars = container.querySelectorAll('.bi-star');
            allStars.forEach((s, i) => {
                if (i < rating) {
                    s.classList.remove('bi-star');
                    s.classList.add('bi-star-fill');
                } else {
                    s.classList.remove('bi-star-fill');
                    s.classList.add('bi-star');
                }
            });
        });
    });
}

// Print functionality
function printRecipe() {
    window.print();
}

// Share functionality
async function shareRecipe(url, title) {
    if (navigator.share) {
        try {
            await navigator.share({
                title: title,
                url: url
            });
        } catch (err) {
            console.log('Error sharing:', err);
        }
    } else {
        // Fallback: copy to clipboard
        navigator.clipboard.writeText(url).then(() => {
            alert('Recipe link copied to clipboard!');
        });
    }
}