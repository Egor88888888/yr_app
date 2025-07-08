const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// Categories data
const categories = [
    { id: 1, name: "Семейное право", icon: "👨‍👩‍👧" },
    { id: 2, name: "Наследство", icon: "📜" },
    { id: 3, name: "Трудовые споры", icon: "💼" },
    { id: 4, name: "Жилищные вопросы", icon: "🏠" },
    { id: 5, name: "Банкротство физлиц", icon: "💰" },
    { id: 6, name: "Налоговые консультации", icon: "📊" },
    { id: 7, name: "Административные дела", icon: "🚔" },
    { id: 8, name: "Арбитраж / бизнес", icon: "🏢" },
    { id: 9, name: "Защита прав потребителей", icon: "🛡️" },
    { id: 10, name: "Миграционное право", icon: "✈️" },
    { id: 11, name: "Уголовные дела", icon: "⚖️" },
    { id: 12, name: "Другое", icon: "📋" }
];

// State
let currentStep = 1;
let uploadedFiles = [];
let formData = {
    category_id: null,
    category_name: "",
    subcategory: "",
    description: "",
    name: "",
    phone: "",
    email: "",
    contact_method: "",
    contact_time: "any",
    files: [],
    tg_user_id: tg.initDataUnsafe?.user?.id || null,
    utm_source: new URLSearchParams(tg.initData).get('start_param') || null
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    renderCategories();
    updateUI();
    
    // Set user name if available
    if (tg.initDataUnsafe?.user) {
        const user = tg.initDataUnsafe.user;
        document.getElementById('name').value = 
            `${user.first_name || ''} ${user.last_name || ''}`.trim();
    }
});

// Render categories
function renderCategories() {
    const container = document.getElementById('categories');
    container.innerHTML = categories.map(cat => `
        <div class="mobile-category-card" data-id="${cat.id}" data-name="${cat.name}">
            <div class="emoji">${cat.icon}</div>
            <div class="text">${cat.name}</div>
        </div>
    `).join('');
    
    // Add click handlers
    container.querySelectorAll('.mobile-category-card').forEach(card => {
        card.addEventListener('click', () => {
            // Remove previous selection
            container.querySelectorAll('.mobile-category-card').forEach(c => {
                c.classList.remove('selected');
            });
            
            // Add selected class for mobile styling
            card.classList.add('selected');
            
            formData.category_id = parseInt(card.dataset.id);
            formData.category_name = card.dataset.name;
            
            // Show selected category info with mobile classes
            const selectedCategoryDiv = document.getElementById('selected-category');
            selectedCategoryDiv.classList.remove('hidden', 'mobile-hidden');
            document.getElementById('selected-category-name').textContent = card.dataset.name;
            
            // Auto-advance after short delay (optional)
            // setTimeout(() => nextStep(), 1000);
        });
    });
}

// Navigation
function nextStep() {
    // Validate current step before proceeding
    if (!validateCurrentStep()) {
        return;
    }
    
    // Collect data from current step
    collectStepData();
    
    if (currentStep < 4) {
        currentStep++;
        updateUI();
    } else {
        submitForm();
    }
}

function prevStep() {
    if (currentStep > 1) {
        currentStep--;
        updateUI();
    }
}

// New validation function for each step
function validateCurrentStep() {
    switch (currentStep) {
        case 1:
            if (!formData.category_id) {
                tg.showAlert ? tg.showAlert('Выберите категорию услуг') : alert('Выберите категорию услуг');
                return false;
            }
            return true;
            
        case 2:
            // Step 2 is optional, but collect data
            return true;
            
        case 3:
            return validateStep3();
            
        case 4:
            return true;
            
        default:
            return true;
    }
}

// Collect data from current step
function collectStepData() {
    switch (currentStep) {
        case 2:
            formData.subcategory = document.getElementById('subcategory').value.trim();
            formData.description = document.getElementById('description').value.trim();
            break;
            
        case 3:
            formData.name = document.getElementById('name').value.trim();
            formData.phone = document.getElementById('phone').value.trim();
            formData.email = document.getElementById('email').value.trim();
            formData.contact_method = document.getElementById('contact-method').value;
            formData.contact_time = document.getElementById('contact-time').value;
            break;
    }
}

// Enhanced validation for step 3
function validateStep3() {
    const name = document.getElementById('name').value.trim();
    const phone = document.getElementById('phone').value.trim();
    const contactMethod = document.getElementById('contact-method').value;
    
    if (!name) {
        tg.showAlert ? tg.showAlert('Введите ваше имя') : alert('Введите ваше имя');
        document.getElementById('name').focus();
        return false;
    }
    
    if (!phone) {
        tg.showAlert ? tg.showAlert('Введите номер телефона') : alert('Введите номер телефона');
        document.getElementById('phone').focus();
        return false;
    }
    
    // Basic phone validation
    const phoneRegex = /^[\+]?[0-9\s\-\(\)]{10,}$/;
    if (!phoneRegex.test(phone)) {
        tg.showAlert ? tg.showAlert('Введите корректный номер телефона') : alert('Введите корректный номер телефона');
        document.getElementById('phone').focus();
        return false;
    }
    
    if (!contactMethod) {
        tg.showAlert ? tg.showAlert('Выберите способ связи') : alert('Выберите способ связи');
        document.getElementById('contact-method').focus();
        return false;
    }
    
    return true;
}

// Update UI
function updateUI() {
    // Hide all steps
    document.querySelectorAll('.step').forEach(step => {
        step.classList.add('hidden', 'mobile-hidden');
    });
    
    // Show current step
    const currentStepElement = document.getElementById(`step-${currentStep}`);
    if (currentStepElement) {
        currentStepElement.classList.remove('hidden', 'mobile-hidden');
    }
    
    // Update progress
    document.getElementById('step-indicator').textContent = `Шаг ${currentStep} из 4`;
    document.getElementById('progress-bar').style.width = `${currentStep * 25}%`;
    
    // Update web buttons visibility
    updateWebButtons();
    
    // Update Telegram buttons (if available)
    if (window.Telegram && tg.initData) {
        updateTelegramButtons();
    }
}

// Update web navigation buttons
function updateWebButtons() {
    // Update back buttons visibility
    const backButtons = document.querySelectorAll('button[onclick="prevStep()"]');
    backButtons.forEach(button => {
        button.style.display = currentStep === 1 ? 'none' : 'block';
    });
    
    // Update category selection visibility
    const selectedCategory = document.getElementById('selected-category');
    if (currentStep === 1 && !formData.category_id) {
        selectedCategory.classList.add('hidden', 'mobile-hidden');
    }
    
    // Special handling for step 4 (review)
    if (currentStep === 4) {
        showReview();
    }
}

// Update Telegram buttons (separate function for clarity)
function updateTelegramButtons() {
    if (currentStep === 1) {
        tg.BackButton.hide();
        tg.MainButton.hide();
    } else {
        tg.BackButton.show();
        tg.BackButton.onClick(prevStep);
        
        if (currentStep === 4) {
            // Review step
            showReview();
            tg.MainButton.text = "Отправить заявку";
            tg.MainButton.color = "#22c55e";
        } else {
            tg.MainButton.text = "Далее";
            tg.MainButton.color = "#3b82f6";
        }
        
        tg.MainButton.show();
        tg.MainButton.onClick(nextStep);
    }
}

// File handling
function handleFiles(files) {
    const fileList = document.getElementById('file-list');
    
    Array.from(files).forEach(file => {
        if (file.size > 10 * 1024 * 1024) {
            tg.showAlert(`Файл ${file.name} слишком большой (макс. 10MB)`);
            return;
        }
        
        if (uploadedFiles.length >= 5) {
            tg.showAlert('Максимум 5 файлов');
            return;
        }
        
        const reader = new FileReader();
        reader.onload = function(e) {
            const fileData = {
                name: file.name,
                type: file.type,
                size: file.size,
                data: e.target.result.split(',')[1] // Base64 без префикса
            };
            
            uploadedFiles.push(fileData);
            formData.files = uploadedFiles;
            
            // Add preview
            const preview = document.createElement('div');
            preview.className = 'flex items-center bg-gray-50 p-2 rounded';
            preview.innerHTML = `
                <span class="text-sm">${file.name}</span>
                <span class="text-xs text-gray-500 ml-2">${(file.size/1024).toFixed(1)}KB</span>
                <button type="button" onclick="removeFile(${uploadedFiles.length-1})" 
                        class="ml-auto text-red-500 text-sm">✕</button>
            `;
            fileList.appendChild(preview);
        };
        reader.readAsDataURL(file);
    });
}

function removeFile(index) {
    uploadedFiles.splice(index, 1);
    formData.files = uploadedFiles;
    
    // Refresh file list
    const fileList = document.getElementById('file-list');
    fileList.innerHTML = '';
    uploadedFiles.forEach((file, i) => {
        const preview = document.createElement('div');
        preview.className = 'flex items-center bg-gray-50 p-2 rounded';
        preview.innerHTML = `
            <span class="text-sm">${file.name}</span>
            <span class="text-xs text-gray-500 ml-2">${(file.size/1024).toFixed(1)}KB</span>
            <button type="button" onclick="removeFile(${i})" 
                    class="ml-auto text-red-500 text-sm">✕</button>
        `;
        fileList.appendChild(preview);
    });
}

// Show review
function showReview() {
    formData.subcategory = document.getElementById('subcategory').value.trim();
    formData.description = document.getElementById('description').value.trim();
    
    const contactMethods = {
        'phone': '📞 Телефонный звонок',
        'telegram': '💬 Telegram',
        'email': '📧 Email',
        'whatsapp': '💚 WhatsApp'
    };
    
    const contactTimes = {
        'any': 'В любое время',
        'morning': 'Утром (9:00-12:00)',
        'afternoon': 'Днем (12:00-17:00)',
        'evening': 'Вечером (17:00-20:00)'
    };
    
    const reviewHtml = `
        <div class="mobile-review-item">
            <div class="mobile-review-label">Категория</div>
            <div class="mobile-review-value">${formData.category_name}</div>
        </div>
        ${formData.subcategory ? `
        <div class="mobile-review-item">
            <div class="mobile-review-label">Уточнение</div>
            <div class="mobile-review-value">${formData.subcategory}</div>
        </div>
        ` : ''}
        ${formData.description ? `
        <div class="mobile-review-item">
            <div class="mobile-review-label">Описание</div>
            <div class="mobile-review-value">${formData.description}</div>
        </div>
        ` : ''}
        ${formData.files.length > 0 ? `
        <div class="mobile-review-item">
            <div class="mobile-review-label">Документы</div>
            <div class="mobile-review-value">${formData.files.length} файл(ов)</div>
        </div>
        ` : ''}
        <div class="mobile-review-item">
            <div class="mobile-review-label">Имя</div>
            <div class="mobile-review-value">${formData.name}</div>
        </div>
        <div class="mobile-review-item">
            <div class="mobile-review-label">Телефон</div>
            <div class="mobile-review-value">${formData.phone}</div>
        </div>
        ${formData.email ? `
        <div class="mobile-review-item">
            <div class="mobile-review-label">Email</div>
            <div class="mobile-review-value">${formData.email}</div>
        </div>
        ` : ''}
        <div class="mobile-review-item">
            <div class="mobile-review-label">Способ связи</div>
            <div class="mobile-review-value">${contactMethods[formData.contact_method]}</div>
        </div>
        <div class="mobile-review-item">
            <div class="mobile-review-label">Время связи</div>
            <div class="mobile-review-value">${contactTimes[formData.contact_time]}</div>
        </div>
    `;
    
    document.getElementById('review-content').innerHTML = reviewHtml;
}

// Submit form
async function submitForm() {
    tg.MainButton.showProgress();
    
    try {
        // Get submit URL - try relative first, then full domain
        const submitUrl = window.location.hostname === 'localhost' 
            ? '/submit' 
            : `${window.location.protocol}//${window.location.host}/submit`;
            
        console.log('Submitting to:', submitUrl);
        console.log('Form data:', formData);
        
        const response = await fetch(submitUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('Result:', result);
        
        if (result.status === 'ok') {
            // Show success with mobile classes
            document.querySelectorAll('.step').forEach(step => {
                step.classList.add('hidden', 'mobile-hidden');
            });
            document.getElementById('success').classList.remove('hidden', 'mobile-hidden');
            
            // Show payment if needed
            if (result.pay_url && result.pay_url !== '# Платежная система не настроена') {
                document.getElementById('payment-section').classList.remove('hidden', 'mobile-hidden');
                document.getElementById('pay-button').href = result.pay_url;
            }
            
            // Hide telegram buttons
            tg.MainButton.hide();
            tg.BackButton.hide();
            
            // Close app after delay
            setTimeout(() => {
                tg.close();
            }, 5000);
        } else {
            tg.showAlert(`Ошибка: ${result.error || 'Неизвестная ошибка'}`);
        }
    } catch (error) {
        console.error('Submit error:', error);
        tg.showAlert(`Ошибка отправки: ${error.message}. Проверьте соединение.`);
    } finally {
        tg.MainButton.hideProgress();
    }
} 