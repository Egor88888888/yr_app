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
        <div class="category-card bg-white p-4 rounded-lg border-2 border-gray-200 cursor-pointer hover:border-blue-500 transition-all flex items-center"
             data-id="${cat.id}" data-name="${cat.name}">
            <div class="text-2xl mr-4">${cat.icon}</div>
            <div class="font-medium text-left">${cat.name}</div>
            <div class="ml-auto text-gray-400">›</div>
        </div>
    `).join('');
    
    // Add click handlers
    container.querySelectorAll('.category-card').forEach(card => {
        card.addEventListener('click', () => {
            // Visual feedback
            card.style.borderColor = '#3b82f6';
            card.style.backgroundColor = '#eff6ff';
            
            formData.category_id = parseInt(card.dataset.id);
            formData.category_name = card.dataset.name;
            
            setTimeout(() => nextStep(), 200);
        });
    });
}

// Navigation
function nextStep() {
    if (currentStep === 3 && !validateStep3()) return;
    
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

// Update UI
function updateUI() {
    // Hide all steps
    document.querySelectorAll('.step').forEach(step => step.classList.add('hidden'));
    
    // Show current step
    document.getElementById(`step-${currentStep}`).classList.remove('hidden');
    
    // Update progress
    document.getElementById('step-indicator').textContent = `Шаг ${currentStep} из 4`;
    document.getElementById('progress-bar').style.width = `${currentStep * 25}%`;
    
    // Update Telegram buttons
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

// Validation
function validateStep3() {
    formData.name = document.getElementById('name').value.trim();
    formData.phone = document.getElementById('phone').value.trim();
    formData.email = document.getElementById('email').value.trim();
    formData.contact_method = document.getElementById('contact-method').value;
    formData.contact_time = document.getElementById('contact-time').value;
    
    if (!formData.name || !formData.phone || !formData.contact_method) {
        tg.showAlert('Пожалуйста, заполните все обязательные поля');
        return false;
    }
    
    // Simple phone validation
    const phoneRegex = /^[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,9}$/;
    if (!phoneRegex.test(formData.phone)) {
        tg.showAlert('Пожалуйста, введите корректный номер телефона');
        return false;
    }
    
    return true;
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
        <div class="border-b pb-3">
            <div class="text-sm text-gray-600">Категория</div>
            <div class="font-medium">${formData.category_name}</div>
        </div>
        ${formData.subcategory ? `
        <div class="border-b pb-3">
            <div class="text-sm text-gray-600">Уточнение</div>
            <div class="font-medium">${formData.subcategory}</div>
        </div>
        ` : ''}
        ${formData.description ? `
        <div class="border-b pb-3">
            <div class="text-sm text-gray-600">Описание</div>
            <div class="font-medium">${formData.description}</div>
        </div>
        ` : ''}
        ${formData.files.length > 0 ? `
        <div class="border-b pb-3">
            <div class="text-sm text-gray-600">Документы</div>
            <div class="font-medium">${formData.files.length} файл(ов)</div>
        </div>
        ` : ''}
        <div class="border-b pb-3">
            <div class="text-sm text-gray-600">Имя</div>
            <div class="font-medium">${formData.name}</div>
        </div>
        <div class="border-b pb-3">
            <div class="text-sm text-gray-600">Телефон</div>
            <div class="font-medium">${formData.phone}</div>
        </div>
        ${formData.email ? `
        <div class="border-b pb-3">
            <div class="text-sm text-gray-600">Email</div>
            <div class="font-medium">${formData.email}</div>
        </div>
        ` : ''}
        <div class="border-b pb-3">
            <div class="text-sm text-gray-600">Способ связи</div>
            <div class="font-medium">${contactMethods[formData.contact_method]}</div>
        </div>
        <div>
            <div class="text-sm text-gray-600">Время связи</div>
            <div class="font-medium">${contactTimes[formData.contact_time]}</div>
        </div>
    `;
    
    document.getElementById('review-content').innerHTML = reviewHtml;
}

// Submit form
async function submitForm() {
    tg.MainButton.showProgress();
    
    try {
        const response = await fetch('/submit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.status === 'ok') {
            // Show success
            document.querySelectorAll('.step').forEach(step => step.classList.add('hidden'));
            document.getElementById('success').classList.remove('hidden');
            
            // Show payment if needed
            if (result.pay_url) {
                document.getElementById('payment-section').classList.remove('hidden');
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
            tg.showAlert('Произошла ошибка. Попробуйте еще раз.');
        }
    } catch (error) {
        tg.showAlert('Ошибка отправки. Проверьте соединение.');
    } finally {
        tg.MainButton.hideProgress();
    }
} 