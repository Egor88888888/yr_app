/*
=======================================================
🚀 ULTRA-MODERN PREMIUM JAVASCRIPT
=======================================================
Революционная система управления состоянием с умным UX
*/

'use strict';

// ===========================
// TELEGRAM WEBAPP INTEGRATION
// ===========================

const tg = window.Telegram?.WebApp || {
    initDataUnsafe: {},
    initData: '',
    MainButton: {
        text: 'Продолжить',
        color: '#667eea',
        textColor: '#FFFFFF',
        isVisible: false,
        isActive: true,
        show() { this.isVisible = true; },
        hide() { this.isVisible = false; },
        setText(text) { this.text = text; },
        onClick(callback) { this.callback = callback; },
        showProgress() { this.isActive = false; },
        hideProgress() { this.isActive = true; }
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
    ready() { console.log('Telegram WebApp ready'); },
    expand() { console.log('Telegram WebApp expanded'); }
};

// Initialize Telegram WebApp
tg.ready();
tg.expand?.();

// ===========================
// PREMIUM CATEGORIES DATA
// ===========================

const ULTRA_CATEGORIES = [
    { id: 1, name: "Семейное право", icon: "👨‍👩‍👧‍👦", color: "#f093fb", description: "Развод, алименты, опека" },
    { id: 2, name: "Корпоративное право", icon: "🏢", color: "#4facfe", description: "Регистрация, договоры, налоги" },
    { id: 3, name: "Недвижимость", icon: "🏠", color: "#11998e", description: "Покупка, продажа, аренда" },
    { id: 4, name: "Трудовое право", icon: "💼", color: "#667eea", description: "Увольнение, зарплата, отпуск" },
    { id: 5, name: "Налоговое право", icon: "💰", color: "#fc4a1a", description: "Декларации, льготы, споры" },
    { id: 6, name: "Административное", icon: "📋", color: "#f7b733", description: "Штрафы, лицензии, разрешения" },
    { id: 7, name: "Уголовное право", icon: "⚖️", color: "#6c5ce7", description: "Защита, представительство" },
    { id: 8, name: "Гражданское право", icon: "📝", color: "#00cec9", description: "Договоры, обязательства, споры" },
    { id: 9, name: "Интеллектуальная собственность", icon: "💡", color: "#00b894", description: "Патенты, товарные знаки" },
    { id: 10, name: "Миграционное право", icon: "✈️", color: "#e17055", description: "Виза, гражданство, РВП" },
    { id: 11, name: "Банкротство", icon: "🛡️", color: "#74b9ff", description: "Физлица, процедуры, защита" },
    { id: 12, name: "Другое", icon: "🔄", color: "#636e72", description: "Иные правовые вопросы" }
];

const CONTACT_METHODS = {
    'telegram': { name: 'Telegram', icon: '💬', color: '#0088cc' },
    'phone': { name: 'Телефонный звонок', icon: '📞', color: '#00c851' },
    'whatsapp': { name: 'WhatsApp', icon: '💚', color: '#25d366' },
    'email': { name: 'Email', icon: '📧', color: '#1976d2' }
};

const CONTACT_TIMES = {
    'any': 'Любое время',
    'morning': 'Утром (9:00-12:00)',
    'afternoon': 'Днём (12:00-17:00)',
    'evening': 'Вечером (17:00-21:00)'
};

// ===========================
// ULTRA-MODERN APP STATE
// ===========================

class UltraModernApp {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.uploadedFiles = [];
        this.isSubmitting = false;
        this.interactions = [];
        this.startTime = Date.now();
        this.debugMessages = [];
        
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

        this.initialize();
    }

    // Visual debug logging
    debugLog(message) {
        console.log(message);
        this.debugMessages.push(message);
        
        const debugElement = document.getElementById('debug-messages');
        if (debugElement) {
            debugElement.innerHTML = this.debugMessages.slice(-5).join('<br>');
        }
    }

    // ===========================
    // INITIALIZATION
    // ===========================

    initialize() {
        this.debugLog('🚀 Initializing Ultra-Modern App...');
        this.debugLog(`📱 Telegram WebApp available: ${!!window.Telegram?.WebApp}`);
        this.debugLog(`🎯 Categories available: ${ULTRA_CATEGORIES.length}`);
        
        this.setupEventListeners();
        this.loadSavedData();
        this.renderCategories();
        this.updateUI();
        this.setupAdvancedFeatures();
        
        this.debugLog('✅ Ultra-Modern App initialized successfully');
        
        // Pre-fill user data from Telegram
        if (tg.initDataUnsafe?.user && !this.formData.name) {
            const user = tg.initDataUnsafe.user;
            this.formData.name = `${user.first_name || ''} ${user.last_name || ''}`.trim();
        }
        
        console.log('🚀 Ultra-Modern App initialized');
    }

    setupEventListeners() {
        // Form inputs with smart debouncing
        document.addEventListener('input', this.debounce(this.handleInputChange.bind(this), 300));
        document.addEventListener('change', this.handleInputChange.bind(this));
        
        // File upload
        const fileInput = document.getElementById('files');
        if (fileInput) {
            fileInput.addEventListener('change', this.handleFileUpload.bind(this));
        }
        
        // Navigation buttons
        const backBtn = document.getElementById('back-btn');
        const nextBtn = document.getElementById('next-btn');
        
        if (backBtn) backBtn.addEventListener('click', this.goToPreviousStep.bind(this));
        if (nextBtn) nextBtn.addEventListener('click', this.goToNextStep.bind(this));
        
        // Character counter for description
        const descriptionField = document.getElementById('description');
        if (descriptionField) {
            descriptionField.addEventListener('input', this.updateCharacterCounter.bind(this));
        }
        
        // Advanced phone formatting
        const phoneField = document.getElementById('phone');
        if (phoneField) {
            phoneField.addEventListener('input', this.formatPhoneNumber.bind(this));
        }
    }

    setupAdvancedFeatures() {
        // Intersection Observer for step tracking
        const stepObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.trackInteraction('step_viewed', { step: entry.target.id });
                }
            });
        });

        document.querySelectorAll('.ultra-step').forEach(step => {
            stepObserver.observe(step);
        });

        // Page visibility for analytics
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.trackInteraction('page_hidden', { step: this.currentStep });
            } else {
                this.trackInteraction('page_visible', { step: this.currentStep });
            }
        });
    }

    // ===========================
    // SMART FORM HANDLING
    // ===========================

    handleInputChange(event) {
        const { id, value } = event.target;
        
        if (this.formData.hasOwnProperty(id)) {
            this.formData[id] = value.trim();
            this.saveDataToStorage();
            this.validateCurrentStep();
            this.trackInteraction('form_input', { field: id, length: value.length });
        }
    }

    updateCharacterCounter() {
        const description = document.getElementById('description');
        const counter = document.getElementById('description-counter');
        
        if (description && counter) {
            const length = description.value.length;
            counter.textContent = length;
            
            // Smart visual feedback
            if (length > 800) {
                counter.style.color = '#fc2c77';
                counter.style.fontWeight = '700';
            } else if (length > 600) {
                counter.style.color = '#f7b733';
                counter.style.fontWeight = '600';
            } else if (length > 200) {
                counter.style.color = '#11998e';
                counter.style.fontWeight = '600';
            } else {
                counter.style.color = '#718096';
                counter.style.fontWeight = '400';
            }
        }
    }

    formatPhoneNumber(event) {
        let value = event.target.value.replace(/\D/g, '');
        
        // Smart Russian phone formatting
        if (value.startsWith('8') && value.length > 1) {
            value = '7' + value.slice(1);
        }
        
        if (value.startsWith('7') && value.length <= 11) {
            const formatted = value.replace(/^7(\d{3})(\d{3})(\d{2})(\d{2})$/, '+7 ($1) $2-$3-$4');
            if (formatted.includes('(') && formatted.includes(')')) {
                event.target.value = formatted;
                this.formData.phone = formatted;
                return;
            }
        }
        
        // Fallback formatting
        if (value.length >= 10) {
            event.target.value = '+7 (' + value.slice(1, 4) + ') ' + value.slice(4, 7) + '-' + value.slice(7, 9) + '-' + value.slice(9, 11);
        }
        
        this.formData.phone = event.target.value;
    }

    // ===========================
    // PREMIUM DATA PERSISTENCE
    // ===========================

    saveDataToStorage() {
        try {
            const dataToSave = {
                ...this.formData,
                currentStep: this.currentStep,
                timestamp: Date.now(),
                version: '2.0'
            };
            localStorage.setItem('ultraApp_data', JSON.stringify(dataToSave));
        } catch (e) {
            console.warn('Could not save to localStorage:', e);
        }
    }

    loadSavedData() {
        try {
            const savedData = localStorage.getItem('ultraApp_data');
            
            if (savedData) {
                const parsed = JSON.parse(savedData);
                
                // Check if data is not too old (24 hours)
                if (Date.now() - parsed.timestamp < 24 * 60 * 60 * 1000) {
                    this.formData = { ...this.formData, ...parsed };
                    this.currentStep = parsed.currentStep || 1;
                }
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
                
                // Trigger events for proper validation
                element.dispatchEvent(new Event('input', { bubbles: true }));
            }
        });
        
        if (this.formData.category_id) {
            this.selectCategory(this.formData.category_id);
        }
    }

    // ===========================
    // REVOLUTIONARY CATEGORY SYSTEM
    // ===========================

    renderCategories() {
        const container = document.getElementById('categories');
        if (!container) {
            this.debugLog('❌ Categories container not found');
            return;
        }

        this.debugLog(`🎯 Rendering categories: ${ULTRA_CATEGORIES.length}`);
        
        container.innerHTML = ULTRA_CATEGORIES.map(category => `
            <div class="ultra-category" 
                 data-id="${category.id}" 
                 data-name="${category.name}"
                 style="--category-color: ${category.color}"
                 title="${category.description}">
                <div class="ultra-category-emoji">${category.icon}</div>
                <div class="ultra-category-text">${category.name}</div>
            </div>
        `).join('');
        
        // Add click handlers properly
        container.querySelectorAll('.ultra-category').forEach(categoryElement => {
            categoryElement.addEventListener('click', () => {
                const categoryId = parseInt(categoryElement.dataset.id);
                this.debugLog(`🎯 Category clicked: ${categoryId}`);
                this.selectCategory(categoryId);
            });
        });
        
        this.debugLog('✅ Categories rendered and handlers attached');
    }

    selectCategory(categoryId) {
        const category = ULTRA_CATEGORIES.find(cat => cat.id === categoryId);
        if (!category) return;

        // Clear previous selection with animation
        document.querySelectorAll('.ultra-category').forEach(card => {
            card.classList.remove('selected');
        });

        // Select new category with premium animation
        const categoryCard = document.querySelector(`[data-id="${categoryId}"]`);
        if (categoryCard) {
            categoryCard.classList.add('selected');
            
            // Premium haptic feedback
            tg.HapticFeedback?.selectionChanged();
            
            // Premium visual feedback
            this.showPremiumRipple(categoryCard);
        }

        // Update form data
        this.formData.category_id = categoryId;
        this.formData.category_name = category.name;

        // Show premium selection feedback
        this.showCategorySelection(category);
        this.saveDataToStorage();
        this.validateCurrentStep();
        this.trackInteraction('category_selected', { categoryId, categoryName: category.name });
    }

    showPremiumRipple(element) {
        const ripple = document.createElement('div');
        ripple.style.cssText = `
            position: absolute;
            border-radius: 50%;
            background: rgba(102, 126, 234, 0.3);
            transform: scale(0);
            animation: premiumRipple 0.6s linear;
            pointer-events: none;
            left: 50%;
            top: 50%;
            width: 20px;
            height: 20px;
            margin-left: -10px;
            margin-top: -10px;
        `;
        
        element.style.position = 'relative';
        element.appendChild(ripple);
        
        setTimeout(() => ripple.remove(), 600);
    }

    showCategorySelection(category) {
        const selectedDiv = document.getElementById('selected-category');
        const selectedName = document.getElementById('selected-category-name');
        
        if (selectedDiv && selectedName) {
            selectedName.textContent = category.name;
            selectedDiv.classList.remove('hidden');
            
            // Premium reveal animation
            selectedDiv.style.opacity = '0';
            selectedDiv.style.transform = 'translateY(-20px) scale(0.95)';
            
            requestAnimationFrame(() => {
                selectedDiv.style.transition = 'all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)';
                selectedDiv.style.opacity = '1';
                selectedDiv.style.transform = 'translateY(0) scale(1)';
            });
        }
    }

    // ===========================
    // ADVANCED FILE HANDLING
    // ===========================

    handleFileUpload(event) {
        const files = Array.from(event.target.files);
        const maxFiles = 5;
        const maxSize = 10 * 1024 * 1024; // 10MB
        
        if (this.uploadedFiles.length + files.length > maxFiles) {
            this.showPremiumToast(`Максимум ${maxFiles} файлов`, 'warning');
            return;
        }

        files.forEach(file => {
            if (file.size > maxSize) {
                this.showPremiumToast(`Файл "${file.name}" слишком большой (максимум 10MB)`, 'error');
                return;
            }

            if (!this.isValidFileType(file)) {
                this.showPremiumToast(`Неподдерживаемый тип файла: ${file.name}`, 'error');
                return;
            }

            this.processFile(file);
        });

        // Clear input
        event.target.value = '';
    }

    isValidFileType(file) {
        const allowedTypes = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'image/jpeg',
            'image/jpg',
            'image/png',
            'text/plain'
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
            
            // Premium success feedback
            tg.HapticFeedback?.notificationOccurred('success');
            this.showPremiumToast(`Файл "${file.name}" добавлен`, 'success');
            
        } catch (error) {
            this.showPremiumToast(`Ошибка загрузки файла: ${file.name}`, 'error');
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
        if (!fileList) return;

        const preview = document.createElement('div');
        preview.className = 'ultra-card ultra-card-compact';
        preview.style.cssText = `
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(79, 172, 254, 0.05));
            border: 1px solid rgba(102, 126, 234, 0.2);
        `;
        
        preview.innerHTML = `
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; font-size: 12px;">
                    ${this.getFileIcon(fileData.type)}
                </div>
                <div>
                    <div style="font-weight: 600; color: #2d3748; font-size: 14px;">${fileData.name}</div>
                    <div style="font-size: 12px; color: #718096;">${this.formatFileSize(fileData.size)}</div>
                </div>
            </div>
            <button type="button" onclick="ultraApp.removeFile('${fileData.id}')" 
                    style="width: 32px; height: 32px; border: none; background: rgba(252, 44, 119, 0.1); color: #fc2c77; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: 700; transition: all 0.2s ease;">
                ×
            </button>
        `;
        
        fileList.appendChild(preview);
    }

    getFileIcon(type) {
        if (type.includes('pdf')) return '📄';
        if (type.includes('word') || type.includes('document')) return '📝';
        if (type.includes('image')) return '🖼️';
        if (type.includes('text')) return '📃';
        return '📎';
    }

    removeFile(fileId) {
        this.uploadedFiles = this.uploadedFiles.filter(file => file.id != fileId);
        this.formData.files = this.uploadedFiles;
        this.saveDataToStorage();
        
        // Re-render file list
        const fileList = document.getElementById('file-list');
        if (fileList) {
            fileList.innerHTML = '';
            this.uploadedFiles.forEach(file => this.renderFilePreview(file));
        }
        
        // Premium feedback
        tg.HapticFeedback?.impactOccurred('light');
        this.showPremiumToast('Файл удалён', 'info');
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // ===========================
    // SMART NAVIGATION
    // ===========================

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
            nextBtn.classList.toggle('ultra-btn-primary', isValid);
            nextBtn.classList.toggle('ultra-btn-secondary', !isValid);
            
            if (this.currentStep === this.totalSteps) {
                nextBtn.innerHTML = this.isSubmitting ? 
                    '⏳ Отправка...' : 
                    '🚀 Отправить заявку';
            } else {
                nextBtn.innerHTML = 'Продолжить →';
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

        // Hide all steps with animation
        document.querySelectorAll('.ultra-step').forEach(stepEl => {
            stepEl.classList.remove('active');
            stepEl.classList.add('hidden');
        });

        // Show current step with premium animation
        const currentStepEl = document.getElementById(`step-${step}`);
        if (currentStepEl) {
            currentStepEl.classList.remove('hidden');
            
            setTimeout(() => {
                currentStepEl.classList.add('active');
            }, 50);
        }

        // Update step indicator and progress
        this.currentStep = step;
        this.updateStepIndicator();
        this.updateProgress();
        this.validateCurrentStep();
        this.saveDataToStorage();

        // Smooth scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });

        // Special handling for review step
        if (step === 4) {
            this.renderReview();
        }

        // Premium haptic feedback
        tg.HapticFeedback?.impactOccurred('light');
        
        this.trackInteraction('step_changed', { from: this.currentStep - 1, to: step });
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
                    message = '🎯 Пожалуйста, выберите категорию услуг';
                }
                break;
            case 3:
                if (!this.formData.name) {
                    message = '👤 Введите ваше имя';
                    this.shakeElement('name');
                } else if (!this.formData.phone) {
                    message = '📱 Введите номер телефона';
                    this.shakeElement('phone');
                } else if (!this.formData.contact_method) {
                    message = '💬 Выберите способ связи';
                    this.shakeElement('contact-method');
                }
                break;
        }

        if (message) {
            this.showPremiumToast(message, 'error');
            tg.HapticFeedback?.notificationOccurred('error');
        }
    }

    // ===========================
    // PREMIUM REVIEW SYSTEM
    // ===========================

    renderReview() {
        const reviewContent = document.getElementById('review-content');
        if (!reviewContent) return;

        const category = ULTRA_CATEGORIES.find(cat => cat.id === this.formData.category_id);
        const contactMethod = CONTACT_METHODS[this.formData.contact_method];
        const contactTime = CONTACT_TIMES[this.formData.contact_time];

        const reviewItems = [
            { label: '🎯 Категория', value: category?.name, important: true },
            { label: '📝 Уточнение', value: this.formData.subcategory },
            { label: '💬 Описание', value: this.formData.description },
            { label: '📎 Документы', value: this.uploadedFiles.length ? `${this.uploadedFiles.length} файл(ов)` : null },
            { label: '👤 Имя', value: this.formData.name, important: true },
            { label: '📱 Телефон', value: this.formData.phone, important: true },
            { label: '📧 Email', value: this.formData.email },
            { label: '💬 Способ связи', value: contactMethod?.name, important: true },
            { label: '⏰ Время связи', value: contactTime }
        ];

        reviewContent.innerHTML = reviewItems
            .filter(item => item.value)
            .map(item => `
                <div style="display: flex; justify-content: space-between; align-items: start; padding: 16px 0; border-bottom: 1px solid rgba(113, 128, 150, 0.1); ${item.important ? 'background: linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(79, 172, 254, 0.02)); margin: 0 -24px; padding-left: 24px; padding-right: 24px;' : ''}">
                    <div style="font-weight: 600; color: #4a5568; font-size: 14px; min-width: 120px;">
                        ${item.label}
                    </div>
                    <div style="color: #2d3748; font-weight: ${item.important ? '600' : '400'}; text-align: right; flex: 1; margin-left: 16px;">
                        ${item.value}
                    </div>
                </div>
            `).join('');
    }

    // ===========================
    // PREMIUM FORM SUBMISSION
    // ===========================

    async submitForm() {
        if (this.isSubmitting) return;

        this.isSubmitting = true;
        this.updateNavigationButtons(false);
        this.trackInteraction('form_submit_start', { formData: this.formData });

        try {
            // Premium loading animation
            tg.MainButton?.showProgress();
            
            const submitUrl = window.location.hostname === 'localhost' 
                ? '/submit' 
                : `${window.location.protocol}//${window.location.host}/submit`;

            console.log('🚀 Submitting to:', submitUrl);
            console.log('📝 Form data:', this.formData);

            const response = await fetch(submitUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-Telegram-Bot-Api-Secret-Token': tg.initData || ''
                },
                body: JSON.stringify({
                    ...this.formData,
                    submission_time: Date.now(),
                    user_agent: navigator.userAgent,
                    app_version: '2.0'
                })
            });

            console.log('📡 Response status:', response.status);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            console.log('✅ Result:', result);

            if (result.status === 'success') {
                this.handleSubmitSuccess(result);
            } else {
                throw new Error(result.message || 'Неизвестная ошибка');
            }

        } catch (error) {
            console.error('❌ Submit error:', error);
            this.handleSubmitError(error);
        } finally {
            this.isSubmitting = false;
            tg.MainButton?.hideProgress();
        }
    }

    handleSubmitSuccess(result) {
        // Hide all steps
        document.querySelectorAll('.ultra-step').forEach(step => {
            step.classList.add('hidden');
            step.classList.remove('active');
        });

        // Show premium success screen
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
        const navigation = document.querySelector('.ultra-navigation');
        if (navigation) navigation.style.display = 'none';

        // Clear saved data
        this.clearSavedData();

        // Send admin notification
        this.sendAdminNotification(result.id);

        // Premium success feedback
        tg.HapticFeedback?.notificationOccurred('success');
        this.showPremiumToast('🎉 Заявка успешно отправлена!', 'success');

        // Auto-close after delay
        setTimeout(() => {
            if (tg.close) {
                tg.close();
            } else if (window.close) {
                window.close();
            }
        }, 3000);

        this.trackInteraction('form_submit_success', { result });
    }

    handleSubmitError(error) {
        let message = '😔 Произошла ошибка при отправке заявки. ';
        
        if (error.message.includes('401')) {
            message += 'Проблема с авторизацией.';
        } else if (error.message.includes('400')) {
            message += 'Проверьте правильность данных.';
        } else if (error.message.includes('500')) {
            message += 'Проблема на сервере.';
        } else {
            message += 'Попробуйте ещё раз.';
        }

        this.showPremiumToast(message, 'error');
        tg.HapticFeedback?.notificationOccurred('error');
        this.trackInteraction('form_submit_error', { error: error.message });
    }

    async sendAdminNotification(applicationId) {
        try {
            const notifyUrl = window.location.hostname === 'localhost' 
                ? '/notify-client' 
                : `${window.location.protocol}//${window.location.host}/notify-client`;
            
            const notificationData = {
                application_id: applicationId,
                user_data: {
                    name: this.formData.name,
                    phone: this.formData.phone,
                    email: this.formData.email || '',
                    category_name: this.formData.category_name,
                    subcategory: this.formData.subcategory || '',
                    description: this.formData.description || '',
                    contact_method: this.formData.contact_method,
                    contact_time: this.formData.contact_time
                }
            };
            
            console.log('📨 Sending admin notification:', notificationData);
            
            const response = await fetch(notifyUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(notificationData)
            });
            
            if (!response.ok) {
                console.error('❌ Failed to send admin notification:', response.status);
            } else {
                console.log('✅ Admin notification sent successfully');
            }
        } catch (error) {
            console.error('❌ Admin notification error:', error);
        }
    }

    // ===========================
    // PREMIUM UI COMPONENTS
    // ===========================

    showPremiumToast(message, type = 'info') {
        const toastColors = {
            success: { bg: 'rgba(17, 153, 142, 0.9)', color: '#ffffff', border: '#11998e' },
            error: { bg: 'rgba(252, 44, 119, 0.9)', color: '#ffffff', border: '#fc2c77' },
            warning: { bg: 'rgba(247, 183, 51, 0.9)', color: '#ffffff', border: '#f7b733' },
            info: { bg: 'rgba(102, 126, 234, 0.9)', color: '#ffffff', border: '#667eea' }
        };

        const icons = {
            success: '✅',
            error: '❌', 
            warning: '⚠️',
            info: 'ℹ️'
        };

        const colors = toastColors[type] || toastColors.info;
        const icon = icons[type] || icons.info;

        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            left: 16px;
            right: 16px;
            background: ${colors.bg};
            color: ${colors.color};
            border: 2px solid ${colors.border};
            border-radius: 16px;
            padding: 16px 20px;
            z-index: 10000;
            font-weight: 600;
            font-size: 14px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            backdrop-filter: blur(20px);
            transform: translateY(-100%);
            transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            display: flex;
            align-items: center;
            gap: 12px;
        `;

        toast.innerHTML = `
            <span style="font-size: 18px;">${icon}</span>
            <span style="flex: 1;">${message}</span>
        `;

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
            }, 400);
        }, 4000);
    }

    shakeElement(elementId) {
        const element = document.getElementById(elementId);
        if (!element) return;

        element.style.animation = 'ultraShake 0.5s ease-in-out';
        element.style.borderColor = '#fc2c77';

        setTimeout(() => {
            element.style.animation = '';
            element.style.borderColor = '';
        }, 500);
    }

    // ===========================
    // ANALYTICS & TRACKING
    // ===========================

    trackInteraction(event, data = {}) {
        const interaction = {
            event,
            data,
            timestamp: Date.now(),
            step: this.currentStep,
            sessionTime: Date.now() - this.startTime
        };

        this.interactions.push(interaction);
        console.log('📊 Interaction:', interaction);

        // Send to analytics if available
        if (window.gtag) {
            window.gtag('event', event, data);
        }
    }

    // ===========================
    // UTILITIES
    // ===========================

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    clearSavedData() {
        try {
            localStorage.removeItem('ultraApp_data');
        } catch (e) {
            console.warn('Could not clear localStorage:', e);
        }
    }
}

// ===========================
// CSS ANIMATIONS
// ===========================

const style = document.createElement('style');
style.textContent = `
    @keyframes premiumRipple {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
    
    @keyframes ultraShake {
        0%, 100% { transform: translateX(0); }
        10%, 30%, 50%, 70%, 90% { transform: translateX(-8px); }
        20%, 40%, 60%, 80% { transform: translateX(8px); }
    }
`;
document.head.appendChild(style);

// ===========================
// INITIALIZATION
// ===========================

let ultraApp;

document.addEventListener('DOMContentLoaded', () => {
    // Show immediate debug info
    const debugElement = document.getElementById('debug-messages');
    if (debugElement) {
        debugElement.innerHTML = '📱 DOM Content Loaded<br>🚀 Creating UltraModernApp...';
    }
    
    // Initialize Ultra-Modern App
    ultraApp = new UltraModernApp();
    
    // Make globally available
    window.ultraApp = ultraApp;
    
    // Add close button handler
    const closeBtn = document.getElementById('close-app-btn');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            console.log('🚪 Close button clicked');
            if (tg.close) {
                tg.close();
            } else if (window.close) {
                window.close();
            } else {
                console.log('⚠️ No close method available');
            }
        });
    }
    
    console.log('🚀 Ultra-Modern Premium App loaded successfully!');
});

// ===========================
// GLOBAL ERROR HANDLING
// ===========================

window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
    if (ultraApp) {
        ultraApp.showPremiumToast('Произошла техническая ошибка', 'error');
        ultraApp.trackInteraction('error', { message: e.message, filename: e.filename });
    }
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
    if (ultraApp) {
        ultraApp.showPremiumToast('Произошла техническая ошибка', 'error');
        ultraApp.trackInteraction('promise_rejection', { reason: e.reason });
    }
});

// Export for debugging
if (typeof window !== 'undefined') {
    window.ultraDebug = {
        getState: () => ultraApp,
        getFormData: () => ultraApp?.formData,
        getCurrentStep: () => ultraApp?.currentStep,
        getInteractions: () => ultraApp?.interactions,
        getUploadedFiles: () => ultraApp?.uploadedFiles
    };
}