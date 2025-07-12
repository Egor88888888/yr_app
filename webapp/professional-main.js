/*
=======================================================
🏆 PROFESSIONAL MINI APP JAVASCRIPT
=======================================================
Современная система управления состоянием и UX
Оптимизирована для идеального клиентского пути
*/

'use strict';

// ===========================
// TELEGRAM WEB APP INTEGRATION
// ===========================

const tg = window.Telegram?.WebApp || {
    initDataUnsafe: {},
    initData: '',
    MainButton: {
        text: 'Продолжить',
        color: '#3b82f6',
        textColor: '#FFFFFF',
        isVisible: false,
        isActive: true,
        show() { this.isVisible = true; },
        hide() { this.isVisible = false; },
        setText(text) { this.text = text; },
        onClick(callback) { this.callback = callback; },
        showProgress() { this.isActive = false; },
        hideProgress() { this.isActive = true; },
        enable() { this.isActive = true; },
        disable() { this.isActive = false; }
    },
    BackButton: {
        isVisible: false,
        show() { this.isVisible = true; },
        hide() { this.isVisible = false; },
        onClick(callback) { this.callback = callback; }
    },
    HapticFeedback: {
        impactOccurred(style) { console.log('Haptic:', style); },
        notificationOccurred(type) { console.log('Notification:', type); },
        selectionChanged() { console.log('Selection changed'); }
    },
    close() { window.close(); },
    ready() { console.log('Telegram WebApp ready'); }
};

// Initialize Telegram WebApp
tg.ready();
tg.expand?.();

// ===========================
// CATEGORIES DATA
// ===========================

const CATEGORIES = [
    { id: 1, name: "Семейное право", icon: "👨‍👩‍👧‍👦", color: "#f59e0b" },
    { id: 2, name: "Корпоративное право", icon: "🏢", color: "#3b82f6" },
    { id: 3, name: "Недвижимость", icon: "🏠", color: "#10b981" },
    { id: 4, name: "Трудовое право", icon: "💼", color: "#8b5cf6" },
    { id: 5, name: "Налоговое право", icon: "💰", color: "#ef4444" },
    { id: 6, name: "Административное право", icon: "📋", color: "#f97316" },
    { id: 7, name: "Уголовное право", icon: "⚖️", color: "#6b7280" },
    { id: 8, name: "Гражданское право", icon: "📝", color: "#06b6d4" },
    { id: 9, name: "Интеллектуальная собственность", icon: "💡", color: "#84cc16" },
    { id: 10, name: "Миграционное право", icon: "✈️", color: "#ec4899" },
    { id: 11, name: "Уголовные дела", icon: "🛡️", color: "#6366f1" },
    { id: 12, name: "Другое", icon: "📋", color: "#64748b" }
];

const CONTACT_METHODS = {
    'telegram': 'Telegram',
    'phone': 'Телефонный звонок',
    'whatsapp': 'WhatsApp',
    'email': 'Email'
};

const CONTACT_TIMES = {
    'any': 'Любое время',
    'morning': 'Утром (9:00-12:00)',
    'afternoon': 'Днём (12:00-17:00)',
    'evening': 'Вечером (17:00-21:00)'
};

// ===========================
// APPLICATION STATE
// ===========================

class AppState {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.uploadedFiles = [];
        this.isSubmitting = false;
        
        this.formData = {
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

        this.initializeEventListeners();
        this.loadSavedData();
    }

    initializeEventListeners() {
        // Form inputs auto-save
        document.addEventListener('input', this.handleInputChange.bind(this));
        document.addEventListener('change', this.handleInputChange.bind(this));
        
        // File upload
        document.getElementById('files').addEventListener('change', this.handleFileUpload.bind(this));
        
        // Navigation buttons
        document.getElementById('back-btn').addEventListener('click', this.goToPreviousStep.bind(this));
        document.getElementById('next-btn').addEventListener('click', this.goToNextStep.bind(this));
        
        // Character counter for description
        const descriptionField = document.getElementById('description');
        if (descriptionField) {
            descriptionField.addEventListener('input', this.updateCharacterCounter.bind(this));
        }
        
        // Phone number formatting
        const phoneField = document.getElementById('phone');
        if (phoneField) {
            phoneField.addEventListener('input', this.formatPhoneNumber.bind(this));
        }
    }

    handleInputChange(event) {
        const { id, value } = event.target;
        
        if (this.formData.hasOwnProperty(id)) {
            this.formData[id] = value.trim();
            this.saveDataToStorage();
            this.validateCurrentStep();
        }
    }

    updateCharacterCounter() {
        const description = document.getElementById('description');
        const counter = document.getElementById('description-counter');
        
        if (description && counter) {
            const length = description.value.length;
            counter.textContent = length;
            
            // Visual feedback for character limit
            if (length > 800) {
                counter.style.color = '#ef4444';
            } else if (length > 600) {
                counter.style.color = '#f59e0b';
            } else {
                counter.style.color = '#6b7280';
            }
        }
    }

    formatPhoneNumber(event) {
        let value = event.target.value.replace(/\D/g, '');
        
        if (value.startsWith('8') && value.length > 1) {
            value = '7' + value.slice(1);
        }
        
        if (value.startsWith('7') && value.length <= 11) {
            value = value.replace(/^7(\d{3})(\d{3})(\d{2})(\d{2})$/, '+7 ($1) $2-$3-$4');
            value = value.replace(/^7(\d{3})(\d{3})(\d{2})/, '+7 ($1) $2-$3');
            value = value.replace(/^7(\d{3})(\d{3})/, '+7 ($1) $2');
            value = value.replace(/^7(\d{3})/, '+7 ($1');
            value = value.replace(/^7/, '+7 ');
        }
        
        event.target.value = value;
        this.formData.phone = value;
    }

    saveDataToStorage() {
        try {
            localStorage.setItem('legalApp_formData', JSON.stringify(this.formData));
            localStorage.setItem('legalApp_currentStep', this.currentStep.toString());
        } catch (e) {
            console.warn('Could not save to localStorage:', e);
        }
    }

    loadSavedData() {
        try {
            const savedData = localStorage.getItem('legalApp_formData');
            const savedStep = localStorage.getItem('legalApp_currentStep');
            
            if (savedData) {
                this.formData = { ...this.formData, ...JSON.parse(savedData) };
            }
            
            if (savedStep) {
                this.currentStep = parseInt(savedStep, 10);
            }
            
            // Pre-fill user data from Telegram
            if (tg.initDataUnsafe?.user && !this.formData.name) {
                const user = tg.initDataUnsafe.user;
                this.formData.name = `${user.first_name || ''} ${user.last_name || ''}`.trim();
            }
            
            this.restoreFormFields();
        } catch (e) {
            console.warn('Could not load from localStorage:', e);
        }
    }

    restoreFormFields() {
        Object.keys(this.formData).forEach(key => {
            const element = document.getElementById(key);
            if (element && this.formData[key]) {
                element.value = this.formData[key];
            }
        });
        
        if (this.formData.category_id) {
            this.selectCategory(this.formData.category_id);
        }
    }

    selectCategory(categoryId) {
        const category = CATEGORIES.find(cat => cat.id === categoryId);
        if (!category) return;

        // Clear previous selection
        document.querySelectorAll('.pro-category').forEach(card => {
            card.classList.remove('selected');
        });

        // Select new category
        const categoryCard = document.querySelector(`[data-id="${categoryId}"]`);
        if (categoryCard) {
            categoryCard.classList.add('selected');
            
            // Haptic feedback
            tg.HapticFeedback?.selectionChanged();
        }

        // Update form data
        this.formData.category_id = categoryId;
        this.formData.category_name = category.name;

        // Show selection feedback
        this.showCategorySelection(category);
        this.saveDataToStorage();
        this.validateCurrentStep();
    }

    showCategorySelection(category) {
        const selectedDiv = document.getElementById('selected-category');
        const selectedName = document.getElementById('selected-category-name');
        
        if (selectedDiv && selectedName) {
            selectedName.textContent = category.name;
            selectedDiv.classList.remove('hidden');
            
            // Smooth reveal animation
            selectedDiv.style.opacity = '0';
            selectedDiv.style.transform = 'translateY(-10px)';
            
            requestAnimationFrame(() => {
                selectedDiv.style.transition = 'all 0.3s ease';
                selectedDiv.style.opacity = '1';
                selectedDiv.style.transform = 'translateY(0)';
            });
        }
    }

    handleFileUpload(event) {
        const files = Array.from(event.target.files);
        const maxFiles = 5;
        const maxSize = 10 * 1024 * 1024; // 10MB
        
        if (this.uploadedFiles.length + files.length > maxFiles) {
            this.showToast(`Максимум ${maxFiles} файлов`, 'warning');
            return;
        }

        files.forEach(file => {
            if (file.size > maxSize) {
                this.showToast(`Файл "${file.name}" слишком большой (максимум 10MB)`, 'error');
                return;
            }

            if (!this.isValidFileType(file)) {
                this.showToast(`Неподдерживаемый тип файла: ${file.name}`, 'error');
                return;
            }

            this.processFile(file);
        });

        // Clear input for potential re-upload
        event.target.value = '';
    }

    isValidFileType(file) {
        const allowedTypes = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'image/jpeg',
            'image/jpg',
            'image/png'
        ];
        return allowedTypes.includes(file.type);
    }

    async processFile(file) {
        try {
            const base64 = await this.fileToBase64(file);
            const fileData = {
                name: file.name,
                size: file.size,
                type: file.type,
                data: base64,
                id: Date.now() + Math.random()
            };

            this.uploadedFiles.push(fileData);
            this.formData.files = this.uploadedFiles;
            this.renderFilePreview(fileData);
            this.saveDataToStorage();
            
            // Haptic feedback
            tg.HapticFeedback?.notificationOccurred('success');
        } catch (error) {
            this.showToast(`Ошибка загрузки файла: ${file.name}`, 'error');
        }
    }

    fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result.split(',')[1]);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    renderFilePreview(fileData) {
        const fileList = document.getElementById('file-list');
        const preview = document.createElement('div');
        preview.className = 'pro-file-preview';
        preview.innerHTML = `
            <div class="pro-file-info">
                <div class="pro-file-name">${fileData.name}</div>
                <div class="pro-file-size">${this.formatFileSize(fileData.size)}</div>
            </div>
            <button type="button" class="pro-file-remove" onclick="appState.removeFile('${fileData.id}')">
                ×
            </button>
        `;
        fileList.appendChild(preview);
    }

    removeFile(fileId) {
        this.uploadedFiles = this.uploadedFiles.filter(file => file.id != fileId);
        this.formData.files = this.uploadedFiles;
        this.saveDataToStorage();
        
        // Re-render file list
        const fileList = document.getElementById('file-list');
        fileList.innerHTML = '';
        this.uploadedFiles.forEach(file => this.renderFilePreview(file));
        
        // Haptic feedback
        tg.HapticFeedback?.impactOccurred('light');
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    validateCurrentStep() {
        let isValid = false;

        switch (this.currentStep) {
            case 1:
                isValid = !!this.formData.category_id;
                break;
            case 2:
                isValid = true; // Optional step
                break;
            case 3:
                isValid = !!(this.formData.name && this.formData.phone && this.formData.contact_method);
                break;
            case 4:
                isValid = true; // Review step
                break;
        }

        this.updateNavigationButtons(isValid);
        return isValid;
    }

    updateNavigationButtons(isValid) {
        const nextBtn = document.getElementById('next-btn');
        const backBtn = document.getElementById('back-btn');

        // Update next button
        if (nextBtn) {
            nextBtn.disabled = !isValid;
            nextBtn.classList.toggle('pro-btn-primary', isValid);
            nextBtn.classList.toggle('pro-btn-secondary', !isValid);
            
            if (this.currentStep === this.totalSteps) {
                nextBtn.textContent = this.isSubmitting ? 'Отправка...' : 'Отправить заявку';
            } else {
                nextBtn.textContent = 'Продолжить →';
            }
        }

        // Update back button
        if (backBtn) {
            backBtn.style.display = this.currentStep > 1 ? 'block' : 'none';
        }
    }

    goToNextStep() {
        if (!this.validateCurrentStep()) {
            this.showValidationErrors();
            return;
        }

        if (this.currentStep < this.totalSteps) {
            this.setStep(this.currentStep + 1);
        } else {
            this.submitForm();
        }
    }

    goToPreviousStep() {
        if (this.currentStep > 1) {
            this.setStep(this.currentStep - 1);
        }
    }

    setStep(step) {
        if (step < 1 || step > this.totalSteps) return;

        // Hide all steps
        document.querySelectorAll('.pro-step').forEach(stepEl => {
            stepEl.classList.remove('active');
            stepEl.classList.add('hidden');
        });

        // Show current step
        const currentStepEl = document.getElementById(`step-${step}`);
        if (currentStepEl) {
            currentStepEl.classList.remove('hidden');
            currentStepEl.classList.add('active');
        }

        // Update step indicator
        this.currentStep = step;
        this.updateStepIndicator();
        this.updateProgress();
        this.validateCurrentStep();
        this.saveDataToStorage();

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });

        // Special handling for review step
        if (step === 4) {
            this.renderReview();
        }

        // Haptic feedback
        tg.HapticFeedback?.impactOccurred('light');
    }

    updateStepIndicator() {
        const indicator = document.getElementById('step-indicator');
        if (indicator) {
            indicator.textContent = `Шаг ${this.currentStep} из ${this.totalSteps}`;
        }
    }

    updateProgress() {
        const progressBar = document.getElementById('progress-bar');
        if (progressBar) {
            const percentage = (this.currentStep / this.totalSteps) * 100;
            progressBar.style.width = `${percentage}%`;
        }
    }

    showValidationErrors() {
        let message = '';

        switch (this.currentStep) {
            case 1:
                if (!this.formData.category_id) {
                    message = 'Пожалуйста, выберите категорию услуг';
                }
                break;
            case 3:
                if (!this.formData.name) message = 'Введите ваше имя';
                else if (!this.formData.phone) message = 'Введите номер телефона';
                else if (!this.formData.contact_method) message = 'Выберите способ связи';
                break;
        }

        if (message) {
            this.showToast(message, 'error');
            tg.HapticFeedback?.notificationOccurred('error');
        }
    }

    renderReview() {
        const reviewContent = document.getElementById('review-content');
        if (!reviewContent) return;

        const reviewItems = [
            { label: 'Категория', value: this.formData.category_name },
            { label: 'Уточнение', value: this.formData.subcategory },
            { label: 'Описание', value: this.formData.description },
            { label: 'Документы', value: this.uploadedFiles.length ? `${this.uploadedFiles.length} файл(ов)` : 'Не прикреплены' },
            { label: 'Имя', value: this.formData.name },
            { label: 'Телефон', value: this.formData.phone },
            { label: 'Email', value: this.formData.email || 'Не указан' },
            { label: 'Способ связи', value: CONTACT_METHODS[this.formData.contact_method] },
            { label: 'Время связи', value: CONTACT_TIMES[this.formData.contact_time] }
        ];

        reviewContent.innerHTML = reviewItems
            .filter(item => item.value)
            .map(item => `
                <div class="pro-review-item">
                    <div class="pro-review-label">${item.label}</div>
                    <div class="pro-review-value">${item.value}</div>
                </div>
            `).join('');
    }

    async submitForm() {
        if (this.isSubmitting) return;

        this.isSubmitting = true;
        this.updateNavigationButtons(false);

        try {
            const submitUrl = window.location.hostname === 'localhost' 
                ? '/submit' 
                : `${window.location.protocol}//${window.location.host}/submit`;

            console.log('Submitting to:', submitUrl);
            console.log('Form data:', this.formData);

            const response = await fetch(submitUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(this.formData)
            });

            console.log('Response status:', response.status);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            console.log('Result:', result);

            if (result.status === 'ok') {
                this.handleSubmitSuccess(result);
            } else {
                throw new Error(result.message || 'Неизвестная ошибка');
            }

        } catch (error) {
            console.error('Submit error:', error);
            this.handleSubmitError(error);
        } finally {
            this.isSubmitting = false;
            this.updateNavigationButtons(true);
        }
    }

    handleSubmitSuccess(result) {
        // Hide all steps
        document.querySelectorAll('.pro-step').forEach(step => {
            step.classList.add('hidden');
            step.classList.remove('active');
        });

        // Show success screen
        const successScreen = document.getElementById('success');
        if (successScreen) {
            successScreen.classList.remove('hidden');
            successScreen.classList.add('active');
        }

        // Handle payment if needed
        if (result.pay_url && result.pay_url !== '# Платежная система не настроена') {
            const paymentSection = document.getElementById('payment-section');
            const payButton = document.getElementById('pay-button');
            
            if (paymentSection) paymentSection.classList.remove('hidden');
            if (payButton) payButton.href = result.pay_url;
        }

        // Hide navigation
        const navigation = document.querySelector('.pro-navigation');
        if (navigation) navigation.style.display = 'none';

        // Clear saved data
        this.clearSavedData();

        // Haptic feedback
        tg.HapticFeedback?.notificationOccurred('success');

        // Close app after delay
        setTimeout(() => {
            if (tg.close) {
                tg.close();
            } else if (window.close) {
                window.close();
            }
        }, 5000);
    }

    handleSubmitError(error) {
        let message = 'Произошла ошибка при отправке заявки. ';
        
        if (error.message.includes('401')) {
            message += 'Ошибка авторизации.';
        } else if (error.message.includes('400')) {
            message += 'Проверьте правильность заполнения данных.';
        } else if (error.message.includes('500')) {
            message += 'Ошибка сервера.';
        } else {
            message += 'Попробуйте еще раз.';
        }

        this.showToast(message, 'error');
        tg.HapticFeedback?.notificationOccurred('error');
    }

    clearSavedData() {
        try {
            localStorage.removeItem('legalApp_formData');
            localStorage.removeItem('legalApp_currentStep');
        } catch (e) {
            console.warn('Could not clear localStorage:', e);
        }
    }

    showToast(message, type = 'info') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `pro-toast pro-toast-${type}`;
        toast.innerHTML = `
            <div style="display: flex; align-items: center; gap: 12px;">
                <div>
                    ${type === 'success' ? '✅' : type === 'error' ? '❌' : type === 'warning' ? '⚠️' : 'ℹ️'}
                </div>
                <div style="flex: 1; font-weight: 500;">${message}</div>
            </div>
        `;

        // Add toast styles
        Object.assign(toast.style, {
            position: 'fixed',
            top: '20px',
            left: '16px',
            right: '16px',
            background: type === 'error' ? '#fef2f2' : type === 'success' ? '#ecfdf5' : type === 'warning' ? '#fffbeb' : '#f0f9ff',
            color: type === 'error' ? '#dc2626' : type === 'success' ? '#059669' : type === 'warning' ? '#d97706' : '#0284c7',
            border: `1px solid ${type === 'error' ? '#fecaca' : type === 'success' ? '#a7f3d0' : type === 'warning' ? '#fed7aa' : '#bae6fd'}`,
            borderRadius: '12px',
            padding: '16px',
            zIndex: '1000',
            fontSize: '14px',
            boxShadow: '0 10px 25px rgba(0, 0, 0, 0.1)',
            transform: 'translateY(-100%)',
            transition: 'transform 0.3s ease'
        });

        document.body.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.style.transform = 'translateY(0)';
        });

        // Remove after delay
        setTimeout(() => {
            toast.style.transform = 'translateY(-100%)';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 4000);
    }
}

// ===========================
// INITIALIZATION
// ===========================

let appState;

document.addEventListener('DOMContentLoaded', () => {
    // Initialize app state
    appState = new AppState();
    
    // Render categories
    renderCategories();
    
    // Set initial step
    appState.setStep(appState.currentStep);
    
    // Pre-fill user data from Telegram
    if (tg.initDataUnsafe?.user) {
        const user = tg.initDataUnsafe.user;
        const nameField = document.getElementById('name');
        if (nameField && !nameField.value) {
            nameField.value = `${user.first_name || ''} ${user.last_name || ''}`.trim();
            appState.formData.name = nameField.value;
        }
    }
    
    console.log('Professional Mini App initialized');
});

function renderCategories() {
    const categoriesContainer = document.getElementById('categories');
    if (!categoriesContainer) return;

    categoriesContainer.innerHTML = CATEGORIES.map(category => `
        <div class="pro-category" 
             data-id="${category.id}" 
             data-name="${category.name}"
             onclick="appState.selectCategory(${category.id})"
             style="--category-color: ${category.color}">
            <div class="pro-category-emoji">${category.icon}</div>
            <div class="pro-category-text">${category.name}</div>
        </div>
    `).join('');
}

// ===========================
// GLOBAL FUNCTIONS
// ===========================

// Expose functions globally for inline event handlers
window.appState = appState;

// Performance monitoring
window.addEventListener('load', () => {
    const loadTime = Date.now() - window.perfData.start;
    console.log(`Professional Mini App loaded in ${loadTime}ms`);
});

// Error handling
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
    if (appState) {
        appState.showToast('Произошла техническая ошибка', 'error');
    }
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
    if (appState) {
        appState.showToast('Произошла техническая ошибка', 'error');
    }
});

// Export for debugging
if (typeof window !== 'undefined') {
    window.debugApp = {
        state: () => appState,
        formData: () => appState?.formData,
        currentStep: () => appState?.currentStep,
        uploadedFiles: () => appState?.uploadedFiles
    };
}